import paramiko
import time
import os

class SSHRunner:
    def __init__(self, host, port, user, key_path, passphrase=None):
        self.host = host
        self.port = int(port)
        self.user = user
        self.key_path = key_path
        self.passphrase = passphrase
        self.client = None

    def connect(self):
        """Establish SSH connection using key-based auth."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            expanded_key = os.path.expanduser(self.key_path)
            if not os.path.exists(expanded_key):
                raise FileNotFoundError(f"Key file not found: {expanded_key}")

            # Try parsing as RSA, Ed25519, etc.
            try:
                pkey = paramiko.Ed25519Key.from_private_key_file(expanded_key, password=self.passphrase)
            except paramiko.SSHException:
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(expanded_key, password=self.passphrase)
                except paramiko.SSHException:
                    pkey = paramiko.ECDSAKey.from_private_key_file(expanded_key, password=self.passphrase)

            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                pkey=pkey,
                timeout=10,
                banner_timeout=15
            )
            return True, "Connected successfully"
        except Exception as e:
            self.close()
            return False, str(e)

    def close(self):
        """Close the SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def is_connected(self):
        """Check if the transport is active."""
        if self.client and self.client.get_transport():
            return self.client.get_transport().is_active()
        return False

    def run(self, command, timeout=None):
        """Execute a remote command."""
        if not self.is_connected():
            return False, "Not connected"
            
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='replace').strip()
            err = stderr.read().decode('utf-8', errors='replace').strip()
            rc = stdout.channel.recv_exit_status()
            
            output = out
            if err:
                output += f"\n{err}" if out else err
                
            return rc == 0, output
        except Exception as e:
            return False, str(e)

    def run_script(self, script_content):
        """Write script to a temp file, execute it, and clean up."""
        tmp_file = f"/tmp/aml_siem_run_{int(time.time())}.sh"
        
        # 1. Upload content using bash echo (handles simple scripts well)
        # For larger scripts, we use SFTP
        try:
            sftp = self.client.open_sftp()
            with sftp.file(tmp_file, "w") as f:
                f.write(script_content)
            sftp.chmod(tmp_file, 0o755)
            sftp.close()
            
            # 2. Run it
            success, output = self.run(f"bash {tmp_file}")
            
            # 3. Cleanup
            self.run(f"rm -f {tmp_file}")
            
            return success, output
        except Exception as e:
            return False, f"Script execution failed: {e}"
