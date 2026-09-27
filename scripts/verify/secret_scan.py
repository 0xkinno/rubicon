import os
import re
import sys

def main():
    # Regular expressions for potential secrets
    patterns = [
        re.compile(r'WATSONX_API_KEY\s*=\s*([a-zA-Z0-9_\-]{10,})'),
        re.compile(r'["\']?(?:api[_-]?key|secret_key|private_key|auth_token)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', re.I),
        re.compile(r'-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA|PRIVATE)\s+KEY-----'),
    ]

    findings = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.next', 'reference', '.venv', 'venv']]
        for f in files:
            if f.endswith(('.png', '.jpg', '.jpeg', '.ico', '.woff2', '.pyc', '.sig')):
                continue
            path = os.path.join(root, f)
            # Exclude known public keys and gitignored .env
            if 'rubicon-verifier.pub.pem' in path or f == '.env':
                continue
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line_no, line in enumerate(fh, 1):
                        for p in patterns:
                            m = p.search(line)
                            if m:
                                val = m.group(0).strip()
                                # Ignore mock/placeholder strings
                                if 'placeholder' in val.lower() or 'your-' in val.lower() or 'mock' in val.lower() or 'test' in val.lower():
                                    continue
                                findings.append((path, line_no, val[:60]))
            except Exception:
                pass

    if findings:
        print(f"FAILED: Found {len(findings)} potential secrets:")
        for path, line_no, val in findings:
            print(f"  {path}:{line_no} -> {val}")
        return 1
    else:
        print("PASSED: Zero hardcoded secrets, tokens, or private keys found!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
