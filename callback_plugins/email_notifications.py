import os
from ansible.plugins.callback import CallbackBase
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
import yaml

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'email_notifications'

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)
        vault_password = os.getenv('VAULT_PASS')
        if vault_password is None:
            raise ValueError("VAULT_PASS environment variable not set")
        self.loader = DataLoader()
        self.vault = VaultLib([(None, VaultSecret(vault_password.encode('utf-8')))])

    def v2_playbook_on_stats(self, stats):
        failed_hosts = stats.failures.keys()
        unreachable_hosts = stats.dark.keys()

        if failed_hosts or unreachable_hosts:
            subject = "Ansible Playbook Failure/Unreachable Hosts Notification"
            body = "The following hosts had issues:\n\n"
            body += "Failed Hosts:\n" + "\n".join(failed_hosts) + "\n\n"
            body += "Unreachable Hosts:\n" + "\n".join(unreachable_hosts)

            self.send_email(subject, body)

    def is_workstation(self, host):
        workstation_groups = ['workstations']
        host_vars = self._loader.get_vars().get(host, {})
        groups = host_vars.get('group_names', [])
        return any(group in groups for group in workstation_groups)

    def send_email(self, subject, body):
        to_email = "billknig@gmail.com"  # Your email address
        app_password = self.get_vault_var('gmail_app_password')
        print(f"Retrieved app password: '{app_password}'")  # Debugging line

        # Email headers
        headers = f"From: Hal @ Ansible <billknig@gmail.com>\n"
        headers += f"To: {to_email}\n"
        headers += f"Subject: {subject}\n\n"

        # Combine headers and body
        email_message = headers + body

        with open('/tmp/email.txt', 'w') as email_file:
            email_file.write(email_message)
        
        os.system(f'cat /tmp/email.txt | msmtp --host=smtp.gmail.com --port=587 --user=billknig@gmail.com --auth=on --passwordeval="echo {app_password}" --tls --tls-certcheck=off --from=billknig@gmail.com -t {to_email}')

    def get_vault_var(self, var_name):
        vault_file_path = 'group_vars/vault.yml'
        with open(vault_file_path, 'r') as vault_file:
            vault_content = vault_file.read()
            decrypted_content = self.vault.decrypt(vault_content)
            vault_data = yaml.safe_load(decrypted_content)  # Load the decrypted content as YAML
        return vault_data.get(var_name)
