import requests
import winrm
import paramiko
import os

class BaseDNSProvider:
    """Base class untuk semua DNS provider."""
    def __init__(self, server):
        self.server = server

    def create_a_record(self, hostname, ip):
        raise NotImplementedError

    def delete_a_record(self, hostname):
        raise NotImplementedError

    def create_ptr_record(self, ip, hostname):
        raise NotImplementedError

    def delete_ptr_record(self, ip):
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError


class WindowsDNSProvider(BaseDNSProvider):
    """Windows Server DNS via WinRM."""
    def __init__(self, server):
        super().__init__(server)
        self.session = None

    def _connect(self):
        try:
            self.session = winrm.Session(
                f'http://{self.server.host}:{self.server.port or 5985}/wsman',
                auth=(self.server.username, self.server.password)
            )
            return True
        except Exception as e:
            return False

    def test_connection(self):
        try:
            self._connect()
            result = self.session.run_ps('Get-DnsServerZone')
            return result.status_code == 0
        except:
            return False

    def create_a_record(self, hostname, ip):
        try:
            self._connect()
            ps = f"Add-DnsServerResourceRecordA -Name '{hostname}' -ZoneName '{self.server.zone_name}' -IPv4Address '{ip}'"
            result = self.session.run_ps(ps)
            return result.status_code == 0
        except:
            return False

    def delete_a_record(self, hostname):
        try:
            self._connect()
            ps = f"Remove-DnsServerResourceRecord -Name '{hostname}' -ZoneName '{self.server.zone_name}' -RRType A -Force"
            result = self.session.run_ps(ps)
            return result.status_code == 0
        except:
            return False

    def create_ptr_record(self, ip, hostname):
        try:
            self._connect()
            # Ambil octet terakhir dari IP
            octets = ip.split('.')
            ptr_name = octets[-1]
            ps = f"Add-DnsServerResourceRecordPtr -ZoneName '{self.server.reverse_zone}' -Name '{ptr_name}' -PtrDomainName '{hostname}.{self.server.zone_name}'"
            result = self.session.run_ps(ps)
            return result.status_code == 0
        except:
            return False

    def delete_ptr_record(self, ip):
        try:
            self._connect()
            octets = ip.split('.')
            ptr_name = octets[-1]
            ps = f"Remove-DnsServerResourceRecord -ZoneName '{self.server.reverse_zone}' -Name '{ptr_name}' -RRType PTR -Force"
            result = self.session.run_ps(ps)
            return result.status_code == 0
        except:
            return False

    def get_a_records(self):
        """Ambil semua A records dari DNS server."""
        try:
            self._connect()
            ps = f"Get-DnsServerResourceRecord -ZoneName '{self.server.zone_name}' -RRType A"
            result = self.session.run_ps(ps)
            if result.status_code == 0:
                return result.std_out.decode('utf-8')
            return None
        except:
            return None

    def get_ptr_records(self):
        """Ambil semua PTR records dari DNS server."""
        try:
            self._connect()
            ps = f"Get-DnsServerResourceRecord -ZoneName '{self.server.reverse_zone}' -RRType PTR"
            result = self.session.run_ps(ps)
            if result.status_code == 0:
                return result.std_out.decode('utf-8')
            return None
        except:
            return None


class BINDDNSProvider(BaseDNSProvider):
    """BIND DNS via SSH."""
    def __init__(self, server):
        super().__init__(server)
        self.ssh = None

    def _connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.server.host,
                port=self.server.port or 22,
                username=self.server.username,
                password=self.server.password
            )
            return True
        except:
            return False

    def test_connection(self):
        try:
            if self._connect():
                self.ssh.close()
                return True
            return False
        except:
            return False

    def create_a_record(self, hostname, ip):
        try:
            self._connect()
            command = f"echo '{hostname}  IN  A  {ip}' >> /etc/bind/db.{self.server.zone_name} && rndc reload"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            self.ssh.close()
            return exit_status == 0
        except:
            return False

    def delete_a_record(self, hostname):
        try:
            self._connect()
            command = f"sed -i '/^{hostname}  IN  A/d' /etc/bind/db.{self.server.zone_name} && rndc reload"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            self.ssh.close()
            return exit_status == 0
        except:
            return False

    def create_ptr_record(self, ip, hostname):
        try:
            self._connect()
            octets = ip.split('.')
            ptr_name = octets[-1]
            command = f"echo '{ptr_name}  IN  PTR  {hostname}.{self.server.zone_name}.' >> /etc/bind/db.{self.server.reverse_zone} && rndc reload"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            self.ssh.close()
            return exit_status == 0
        except:
            return False

    def delete_ptr_record(self, ip):
        try:
            self._connect()
            octets = ip.split('.')
            ptr_name = octets[-1]
            command = f"sed -i '/^{ptr_name}  IN  PTR/d' /etc/bind/db.{self.server.reverse_zone} && rndc reload"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            self.ssh.close()
            return exit_status == 0
        except:
            return False

    def get_a_records(self):
        """Ambil semua A records dari zone file."""
        try:
            self._connect()
            command = f"cat /etc/bind/db.{self.server.zone_name}"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            records = stdout.read().decode('utf-8')
            self.ssh.close()
            return records
        except:
            return None

    def get_ptr_records(self):
        """Ambil semua PTR records dari reverse zone file."""
        try:
            self._connect()
            command = f"cat /etc/bind/db.{self.server.reverse_zone}"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            records = stdout.read().decode('utf-8')
            self.ssh.close()
            return records
        except:
            return None


class PowerDNSProvider(BaseDNSProvider):
    """PowerDNS via REST API."""
    def __init__(self, server):
        super().__init__(server)
        self.headers = {'X-API-Key': server.api_key}

    def test_connection(self):
        try:
            url = f"{self.server.api_url}/servers/localhost/zones"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False

    def create_a_record(self, hostname, ip):
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.zone_name}"
            fqdn = f"{hostname}.{self.server.zone_name}."
            data = {
                "rrsets": [{
                    "name": fqdn,
                    "type": "A",
                    "ttl": 3600,
                    "changetype": "REPLACE",
                    "records": [{"content": ip, "disabled": False}]
                }]
            }
            response = requests.patch(url, json=data, headers=self.headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delete_a_record(self, hostname):
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.zone_name}"
            fqdn = f"{hostname}.{self.server.zone_name}."
            data = {
                "rrsets": [{
                    "name": fqdn,
                    "type": "A",
                    "ttl": 3600,
                    "changetype": "DELETE"
                }]
            }
            response = requests.patch(url, json=data, headers=self.headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def create_ptr_record(self, ip, hostname):
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.reverse_zone}"
            octets = ip.split('.')
            ptr_name = f"{octets[-1]}.{self.server.reverse_zone}."
            data = {
                "rrsets": [{
                    "name": ptr_name,
                    "type": "PTR",
                    "ttl": 3600,
                    "changetype": "REPLACE",
                    "records": [{"content": f"{hostname}.{self.server.zone_name}.", "disabled": False}]
                }]
            }
            response = requests.patch(url, json=data, headers=self.headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delete_ptr_record(self, ip):
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.reverse_zone}"
            octets = ip.split('.')
            ptr_name = f"{octets[-1]}.{self.server.reverse_zone}."
            data = {
                "rrsets": [{
                    "name": ptr_name,
                    "type": "PTR",
                    "ttl": 3600,
                    "changetype": "DELETE"
                }]
            }
            response = requests.patch(url, json=data, headers=self.headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_a_records(self):
        """Ambil semua A records dari PowerDNS API."""
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.zone_name}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                records = []
                for rrset in data.get('rrsets', []):
                    if rrset['type'] == 'A':
                        for record in rrset['records']:
                            records.append({
                                'name': rrset['name'],
                                'ip': record['content']
                            })
                return records
            return None
        except:
            return None

    def get_ptr_records(self):
        """Ambil semua PTR records dari PowerDNS API."""
        try:
            url = f"{self.server.api_url}/servers/localhost/zones/{self.server.reverse_zone}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                records = []
                for rrset in data.get('rrsets', []):
                    if rrset['type'] == 'PTR':
                        for record in rrset['records']:
                            records.append({
                                'name': rrset['name'],
                                'ptr': record['content']
                            })
                return records
            return None
        except:
            return None


def get_provider(server):
    """Factory function untuk mendapatkan provider yang sesuai."""
    providers = {
        'windows': WindowsDNSProvider,
        'bind': BINDDNSProvider,
        'powerdns': PowerDNSProvider
    }
    provider_class = providers.get(server.provider)
    if provider_class:
        return provider_class(server)
    return None

