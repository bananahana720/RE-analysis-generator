#\!/usr/bin/env python3
"""
API Credential Setup and Validation Tool

This script helps configure and validate API credentials for production deployment.
"""

from pathlib import Path

project_root = Path(__file__).parent.parent.parent

def main():
    print('=' * 60)
    print('API CREDENTIAL SETUP GUIDE')
    print('=' * 60)
    
    env_file = project_root / '.env'
    
    print(f'Environment file: {env_file}')
    print(f'File exists: {env_file.exists()}')
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check for test/placeholder values
        test_keys = []
        if 'test_key' in content:
            test_keys.append('Found test_key placeholders')
        
        print('''
Current issues:''')
        if test_keys:
            for issue in test_keys:
                print(f'  - {issue}')
            
            print('''
Required Actions:''')
            print('1. Get Maricopa County API key:')
            print('   - Visit: https://api.mcassessor.maricopa.gov')
            print('   - Register for API access')
            print('   - Replace MARICOPA_API_KEY=test_key with real key')
            
            print('''
2. Optional: WebShare proxy service (~$5/month):''')
            print('   - Visit: https://proxy.webshare.io') 
            print('   - Sign up for residential proxy plan')
            print('   - Replace WEBSHARE_API_KEY=test_key with real credentials')
            
            print('''
3. Optional: 2captcha service (~$3/month):''')
            print('   - Visit: https://2captcha.com')
            print('   - Add funds and get API key')
            print('   - Replace CAPTCHA_API_KEY=test_key with real key')
        else:
            print('  No test_key placeholders found - credentials may be configured')
    else:
        print('No .env file found - creating template...')
        
        template = """# Phoenix Real Estate Data Collector Configuration

# Database 
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=phoenix_real_estate

# REQUIRED: Maricopa County API (Free)
MARICOPA_API_KEY=your_maricopa_api_key_here

# OPTIONAL: WebShare Proxy (~-5/month)  
WEBSHARE_API_KEY=your_webshare_api_key_here
WEBSHARE_USERNAME=your_webshare_username_here
WEBSHARE_PASSWORD=your_webshare_password_here

# OPTIONAL: 2captcha (~-3/month)
CAPTCHA_API_KEY=your_2captcha_api_key_here

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:latest

# Environment
ENVIRONMENT=production
"""
        
        with open(env_file, 'w') as f:
            f.write(template)
        
        print(f'Created template: {env_file}')
        print('Edit this file with your actual API credentials')

if __name__ == '__main__':
    main()
