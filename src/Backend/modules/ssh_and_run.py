import paramiko
#Paramiko is a Python library that handles SSH connections (securely logging into other computers).
def ssh_execute_command(hostname, username, password, command):
    """
    SSH into a remote host and execute a command.

    Args:
        hostname (str): The hostname or IP address of the remote machine.
        username (str): The username for the SSH connection.
        password (str): The password for the SSH connection.
        command (str): The command to execute on the remote machine.

    Returns:
        str: The output of the command.
    """
    try:
        # Create an SSH client
        ssh_client = paramiko.SSHClient() #Sets up an SSH client that knows how to talk to the remote computer
        # Automatically add the host key if not already known
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #AutoAddPolicy means “if you haven’t seen this computer before, trust it automatically.” (This is for convenience; in production, you might want to be stricter.)
        # Connect to the host
        ssh_client.connect(hostname, username=username, password=password)
        
        # Execute the command
        """
        Runs the command you gave.
        stdin: If you wanted to send input to the command.
        stdout: The output (what the command prints).
        stderr: Any error messages.
        """
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Collect output and error
        output = stdout.read().decode().strip() #Reads what the command printed out (output)
        error = stderr.read().decode().strip() #Reads any error messages (error)
        #Decodes from bytes to a regular string 
        
        # Close the SSH connection
        ssh_client.close()
        
        # Return output or error
        return output if output else error
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    host = "example.com"
    user = "your_username"
    passwd = "your_password"
    cmd = "ls -l"
    result = ssh_execute_command(host, user, passwd, cmd)
    print(result)
