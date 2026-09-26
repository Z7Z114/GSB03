import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import List, Optional, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')


class MarkdownEncryptor:
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or os.getenv("ENCRYPTION_KEY")
        self.fernet = None
        self._init_encryption()

    def _init_encryption(self):
        if self.encryption_key:
            try:
                if len(self.encryption_key) == 32:
                    key = base64.urlsafe_b64encode(self.encryption_key.encode())
                else:
                    salt = b"laser_vibrometry_salt"
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
                
                self.fernet = Fernet(key)
                print("Encryption initialized successfully.")
            except Exception as e:
                print(f"Warning: Could not initialize encryption: {e}")
                self.fernet = None
        else:
            print("Warning: No encryption key provided.")
            self.fernet = None

    def encrypt_markdown(self, markdown_content: str) -> Tuple[bytes, str]:
        if self.fernet is None:
            return markdown_content.encode('utf-8'), "none"

        try:
            encrypted = self.fernet.encrypt(markdown_content.encode('utf-8'))
            return encrypted, "fernet"
        except Exception as e:
            print(f"Encryption failed: {e}")
            return markdown_content.encode('utf-8'), "failed"

    def decrypt_markdown(self, encrypted_data: bytes) -> str:
        if self.fernet is None:
            raise ValueError("未配置加密密钥，无法解密")

        try:
            decrypted = self.fernet.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败：密钥错误或密文已损坏（{e}）") from e

    def save_encrypted_file(self, markdown_content: str, output_path: str) -> Dict:
        encrypted_data, method = self.encrypt_markdown(markdown_content)

        try:
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            return {
                "success": True,
                "file_path": output_path,
                "encryption_method": method,
                "file_size": len(encrypted_data),
                "checksum": self._calculate_checksum(encrypted_data)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def load_encrypted_file(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted = self.decrypt_markdown(encrypted_data)

            return {
                "success": True,
                "content": decrypted,
                "file_size": len(encrypted_data),
                "checksum": self._calculate_checksum(encrypted_data)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _calculate_checksum(self, data: bytes) -> str:
        import hashlib
        return hashlib.sha256(data).hexdigest()


class EmailSender:
    def __init__(self, 
                 smtp_server: Optional[str] = None,
                 smtp_port: Optional[int] = None,
                 smtp_user: Optional[str] = None,
                 smtp_password: Optional[str] = None):
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")

    def send_encrypted_email(self,
                            to_emails: List[str],
                            subject: str,
                            markdown_content: str,
                            encrypted_attachment: Optional[bytes] = None,
                            attachment_filename: str = "meeting_minutes_encrypted.bin",
                            cc_emails: Optional[List[str]] = None,
                            bcc_emails: Optional[List[str]] = None) -> Dict:
        if not all([self.smtp_server, self.smtp_port, self.smtp_user, self.smtp_password]):
            return self._mock_send_email(to_emails, subject, markdown_content)

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(to_emails)
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            msg['Subject'] = Header(subject, 'utf-8')

            body = f"""
这是一封加密的会议纪要邮件。

请注意:
1. 附件为加密的会议纪要文件
2. 请使用对应的解密密钥查看内容
3. 本邮件内容敏感，请勿转发

---
*此邮件由激光测振会议系统自动生成*
            """

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if encrypted_attachment:
                part = MIMEApplication(encrypted_attachment, Name=attachment_filename)
                part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
                msg.attach(part)

            all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, all_recipients, msg.as_string())

            return {
                "success": True,
                "to": to_emails,
                "cc": cc_emails,
                "bcc": bcc_emails,
                "subject": subject,
                "attachment": attachment_filename if encrypted_attachment else None,
                "message": "Email sent successfully"
            }
        except Exception as e:
            print(f"Email sending failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _mock_send_email(self, to_emails: List[str], subject: str, 
                         markdown_content: str) -> Dict:
        return {
            "success": False,
            "to": to_emails,
            "subject": subject,
            "error": "SMTP 未配置，邮件未发送",
            "message": "SMTP not configured; email was NOT sent"
        }


class MeetingMinutesDispatcher:
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryptor = MarkdownEncryptor(encryption_key)
        self.email_sender = EmailSender()

    def generate_and_dispatch(self,
                              markdown_content: str,
                              to_emails: List[str],
                              subject: Optional[str] = None,
                              output_dir: str = "./output",
                              send_email: bool = True) -> Dict:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = self._generate_timestamp()
        encrypted_filename = f"meeting_minutes_{timestamp}.bin"
        encrypted_path = os.path.join(output_dir, encrypted_filename)

        save_result = self.encryptor.save_encrypted_file(markdown_content, encrypted_path)

        if not save_result["success"]:
            return {
                "success": False,
                "error": f"Failed to save encrypted file: {save_result.get('error')}"
            }

        result = {
            "encryption": save_result,
            "email": None,
            "local_path": encrypted_path
        }

        if send_email:
            email_subject = subject or f"[机密] 会议纪要 - {timestamp}"
            
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()

            email_result = self.email_sender.send_encrypted_email(
                to_emails=to_emails,
                subject=email_subject,
                markdown_content=markdown_content,
                encrypted_attachment=encrypted_data,
                attachment_filename=encrypted_filename
            )
            result["email"] = email_result

        return result

    def _generate_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
