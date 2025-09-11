# SSL Certificates

⚠️ **IMPORTANT**: SSL certificate files are now properly ignored by Git. Never commit certificate files to version control!

Place your SSL certificates from your domain provider here:

## Required Files:
- `certificate.crt` - Your SSL certificate (or fullchain.pem)
- `private.key` - Your private key

## Instructions:

### From Domain Provider (Recommended):
1. Download your SSL certificate files from your domain provider's control panel
2. Look for files named something like:
   - Certificate: `certificate.crt`, `domain.crt`, `fullchain.pem`, or `your-domain.crt`
   - Private Key: `private.key`, `domain.key`, or `your-domain.key`
3. Rename them to exactly:
   - `certificate.crt`
   - `private.key`
4. Place both files in this directory

### For Development (Self-signed):
If you don't have domain SSL yet, you can generate self-signed certificates:

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -newkey rsa:4096 -keyout private.key -out certificate.crt -days 365 -nodes -subj "/CN=localhost"
```

## Security Notes:
- Never commit these files to version control
- Keep your private key secure
- Use proper SSL certificates from your domain provider in production
- These files should have restricted permissions (600 or 644)

## File Structure:
```
ssl/
├── README.md          # This file
├── certificate.crt    # Your SSL certificate
└── private.key        # Your private key
```
