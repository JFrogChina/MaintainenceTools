#!/usr/bin/env python3
"""
License Decomposer - Mac M4 Application
Equivalent to: openssl aes-256-cbc -d -md md5 -in <json_FILE_NAME> | jq '.licenses | .[] | .key' | sed 's!\\r\\n!!g'
"""

import json
import sys
import argparse
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import re

class LicenseDecomposer:
    def __init__(self):
        self.password = None
        
    def derive_key_iv_openssl(self, password, salt):
        """Derive key and IV using OpenSSL's EVP_BytesToKey equivalent"""
        # OpenSSL's key derivation method
        d = d_i = b''
        while len(d) < 48:  # 32 bytes key + 16 bytes IV
            hasher = hashes.Hash(hashes.MD5())
            if d_i:
                hasher.update(d_i)
            hasher.update(password.encode())
            hasher.update(salt)
            d_i = hasher.finalize()
            d += d_i
        return d[:32], d[32:48]  # key, iv
     
    def decrypt_aes_256_cbc(self, encrypted_data, password):
        """Decrypt AES-256-CBC encrypted data"""
        try:
            # Check if file starts with "Salted__" (OpenSSL format)
            if encrypted_data.startswith(b'Salted__'):
                # OpenSSL salted format
                salt = encrypted_data[8:16]
                ciphertext = encrypted_data[16:]
                
                # Derive key and IV using OpenSSL method
                key, iv = self.derive_key_iv_openssl(password, salt)
            else:
                # No salt, derive key and IV differently
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                salt = b'\x00' * 8  # Default salt
                kdf = PBKDF2HMAC(
                    algorithm=hashes.MD5(),
                    length=48,  # 32 bytes key + 16 bytes IV
                    salt=salt,
                    iterations=1,
                )
                key_iv = kdf.derive(password.encode())
                key, iv = key_iv[:32], key_iv[32:48]
                ciphertext = encrypted_data
            
            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            padding_length = decrypted[-1]
            if padding_length <= 16 and padding_length > 0:
                decrypted = decrypted[:-padding_length]
            
            # Try to decode as UTF-8
            try:
                return decrypted.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 fails, try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        return decrypted.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # If all encodings fail, return as string with error replacement
                return decrypted.decode('utf-8', errors='replace')
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def extract_license_keys(self, json_data):
        """Extract license keys from JSON data"""
        try:
            data = json.loads(json_data)
            license_keys = []
            
            # Navigate to licenses array
            if 'licenses' in data:
                for license_item in data['licenses']:
                    if isinstance(license_item, dict) and 'key' in license_item:
                        license_keys.append(license_item['key'])
            
            return license_keys
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
    
    def clean_license_keys(self, license_keys):
        """Clean license keys by removing \r\n sequences"""
        cleaned_keys = []
        for key in license_keys:
            # Remove \r\n sequences (both literal and escaped)
            cleaned_key = re.sub(r'\\r\\n', '', key)  # Remove escaped sequences
            cleaned_key = re.sub(r'\r\n', '', cleaned_key)  # Remove actual sequences
            cleaned_keys.append(cleaned_key)
        return cleaned_keys
    
    def process_file(self, file_path, password=None):
        """Process encrypted JSON file and extract license keys"""
        try:
            # Read encrypted file
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # If no password provided, try to prompt
            if password is None:
                import getpass
                password = getpass.getpass("Enter password for decryption: ")
            
            # Decrypt the data
            decrypted_json = self.decrypt_aes_256_cbc(encrypted_data, password)
            
            # Extract license keys
            license_keys = self.extract_license_keys(decrypted_json)
            
            # Clean the keys
            cleaned_keys = self.clean_license_keys(license_keys)
            
            return cleaned_keys
            
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Processing failed: {e}")
    
    def run(self, file_path, password=None, output_file=None):
        """Main execution method"""
        try:
            license_keys = self.process_file(file_path, password)
            
            # Output results
            if output_file:
                with open(output_file, 'w') as f:
                    for key in license_keys:
                        f.write(key + '\n')
                print(f"License keys written to: {output_file}")
            else:
                for key in license_keys:
                    print(key)
                    
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="License Decomposer - Extract license keys from encrypted JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s encrypted_file.json
  %(prog)s encrypted_file.json -p mypassword
  %(prog)s encrypted_file.json -o output.txt
  %(prog)s encrypted_file.json -p mypassword -o output.txt
        """
    )
    
    parser.add_argument("file", help="Encrypted JSON file to process")
    parser.add_argument("-p", "--password", help="Password for decryption")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("--version", action="version", version="License Decomposer 1.0")
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    # Create decomposer and run
    decomposer = LicenseDecomposer()
    decomposer.run(args.file, args.password, args.output)

if __name__ == "__main__":
    main() 