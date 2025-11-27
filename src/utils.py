import docker
import os
import tempfile
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def validate_code_safety(code: str):
    """
    Validate that generated code doesn't contain dangerous operations.
    Returns (is_safe, reason)
    """
    dangerous_patterns = [
        ('os.system', 'Shell command execution'),
        ('subprocess', 'Process execution'),
        ('eval(', 'Dynamic code evaluation'),
        ('exec(', 'Dynamic code execution'),
        ('__import__', 'Dynamic imports'),
        ('requests.', 'Network requests'),
        ('urllib', 'Network requests'),
        ('socket', 'Network sockets'),
    ]
    
    code_lower = code.lower()
    
    for pattern, reason in dangerous_patterns:
        if pattern.lower() in code_lower:
            return False, f"Dangerous operation detected: {reason}"
    
    return True, ""

def execute_in_docker(code, data_path, image_name="retail_insights_executor"):
    """
    Executes the given Python code in a Docker container.
    Mounts the directory containing data_path to /data in the container.
    """
    # Security: Validate code before execution
    is_safe, reason = validate_code_safety(code)
    if not is_safe:
        return {"success": False, "error": f"Security validation failed: {reason}", "plot_path": None}
    
    client = docker.from_env()
    
    # Get the directory of the data file to mount
    data_dir = os.path.dirname(os.path.abspath(data_path))
    data_filename = os.path.basename(data_path)
    container_data_path = f"/data/{data_filename}"
    
    # Inject the correct path into the code
    # Replace the Windows path with the container path
    code = code.replace(data_path, container_data_path)
    code = code.replace(data_path.replace("\\", "/"), container_data_path)
    
    # Create a temporary file for the script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
        script_file.write(code)
        script_path = script_file.name
    
    try:
        # Create output directory for plots
        output_dir = tempfile.mkdtemp()
        
        container = client.containers.run(
            image_name,
            command=["python", "/app/script.py"],
            volumes={
                script_path: {'bind': '/app/script.py', 'mode': 'ro'},
                data_dir: {'bind': '/data', 'mode': 'ro'},
                output_dir: {'bind': '/output', 'mode': 'rw'}
            },
            working_dir="/app",
            stderr=True,
            stdout=True,
            detach=False,
            remove=True
        )
        
        # Check for generated plots
        plot_path = None
        for filename in os.listdir(output_dir):
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                plot_path = os.path.join(output_dir, filename)
                break
        
        return {"success": True, "output": container.decode('utf-8'), "plot_path": plot_path}
    except docker.errors.ContainerError as e:
        return {"success": False, "error": e.stderr.decode('utf-8'), "plot_path": None}
    except Exception as e:
        return {"success": False, "error": str(e), "plot_path": None}
    finally:
        os.remove(script_path)

def build_docker_image(image_name="retail_insights_executor"):
    client = docker.from_env()
    dockerfile_path = os.path.join(os.getcwd(), "docker")
    print(f"Building Docker image {image_name} from {dockerfile_path}...")
    client.images.build(path=dockerfile_path, tag=image_name)
    print("Build complete.")
