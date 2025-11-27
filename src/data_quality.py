"""
Data quality detection and transformation utilities.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def is_valid_header_row(row: List) -> bool:
    """
    Check if a row looks like a valid header.
    Returns True if row appears to be descriptive column names.
    """
    if not row or len(row) == 0:
        return False
    
    # Must be mostly strings
    string_count = sum(isinstance(val, str) and not str(val).replace('.','').replace('-','').isdigit() for val in row if pd.notna(val))
    if string_count / len(row) < 0.7:
        return False
    
    # Should have meaningful names (not all single chars or numbers)
    meaningful = sum(len(str(val).strip()) > 2 for val in row if pd.notna(val))
    if meaningful / len(row) < 0.5:
        return False
    
    return True

def detect_header_issues(df: pd.DataFrame) -> Optional[str]:
    """
    Detect and classify header issues.
    Returns: None, 'promote_row_1_as_header', or 'fix_column_names'
    """
    current_header = df.columns
    
    # Check if current header has issues
    has_unnamed = any('Unnamed' in str(col) for col in current_header)
    has_empty = any(str(col).strip() == '' for col in current_header)
    all_numeric = all(str(col).replace('.','').replace('-','').isdigit() for col in current_header if col)
    
    # If header is bad, check if row 1 (index 0) looks like a valid header
    if (has_unnamed or has_empty or all_numeric) and len(df) > 0:
        row_1 = df.iloc[0].tolist()
        if is_valid_header_row(row_1):
            return "promote_row_1_as_header"
    
    # Otherwise, just fix bad column names in place
    if has_unnamed or has_empty:
        return "fix_column_names"
    
    return None  # No issues

def apply_header_fix(df: pd.DataFrame, action: str) -> pd.DataFrame:
    """Apply the recommended header transformation."""
    if action == "promote_row_1_as_header":
        # Use first data row as header
        new_header = df.iloc[0].tolist()
        df = df[1:].reset_index(drop=True)
        df.columns = new_header
        logger.info("Promoted row 1 to header")
    elif action == "fix_column_names":
        # Replace bad names with generic Col_1, Col_2, etc.
        new_cols = []
        for i, col in enumerate(df.columns):
            if 'Unnamed' in str(col) or str(col).strip() == '':
                new_cols.append(f"Column_{i+1}")
            else:
                new_cols.append(col)
        df.columns = new_cols
        logger.info(f"Fixed {sum(1 for c in df.columns if 'Column_' in str(c))} column names")
    
    return df

def detect_data_quality_issues(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive data quality analysis.
    Returns dict with issues found.
    """
    issues = {}
    
    # Missing values
    missing = df.isnull().sum()
    if missing.sum() > 0:
        issues['missing_values'] = missing[missing > 0].to_dict()
    
    # Duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues['duplicate_rows'] = int(duplicates)
    
    # Check for outliers in numeric columns (simple Z-score method)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outliers = {}
    for col in numeric_cols:
        if df[col].std() > 0:  # Avoid division by zero
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            outlier_count = (z_scores > 3).sum()
            if outlier_count > 0:
                outliers[col] = int(outlier_count)
    
    if outliers:
        issues['outliers'] = outliers
    
    # Header issues
    header_action = detect_header_issues(df)
    if header_action:
        issues['header_issue'] = header_action
    
    return issues

def generate_quality_report(df: pd.DataFrame) -> Tuple[Dict[str, Any], bool]:
    """
    Generate full quality report.
    Returns: (report_dict, needs_transformation)
    """
    issues = detect_data_quality_issues(df)
    
    report = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'issues_found': issues,
        'transformations_suggested': []
    }
    
    # Generate transformation suggestions
    if 'header_issue' in issues:
        if issues['header_issue'] == 'promote_row_1_as_header':
            report['transformations_suggested'].append({
                'type': 'header',
                'action': 'promote_row_1',
                'description': 'First row appears to contain column headers'
            })
        elif issues['header_issue'] == 'fix_column_names':
            report['transformations_suggested'].append({
                'type': 'header',
                'action': 'fix_names',
                'description': 'Some column names are missing or invalid'
            })
    
    if 'duplicate_rows' in issues:
        report['transformations_suggested'].append({
            'type': 'duplicates',
            'action': 'remove',
            'description': f'{issues["duplicate_rows"]} duplicate rows found'
        })
    
    needs_transformation = len(report['transformations_suggested']) > 0
    
    return report, needs_transformation
