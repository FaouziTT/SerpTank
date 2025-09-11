#!/usr/bin/env node
/**
 * Script to set up OpenAPI TypeScript generation
 * 
 * This script configures the frontend to generate TypeScript types
 * from the backend's OpenAPI schema.
 */

const fs = require('fs');
const path = require('path');

// Configuration for @hey-api/openapi-ts
const config = {
  name: '@hey-api/openapi-ts',
  input: 'http://localhost:8000/api/v1/openapi.json',
  output: './types/generated',
  types: {
    enums: 'javascript',
  },
  services: {
    asClass: true,
  },
  client: 'axios',
};

// Create configuration file
const configPath = path.join(__dirname, '..', 'openapi-ts.config.js');
const configContent = `module.exports = ${JSON.stringify(config, null, 2)};`;

fs.writeFileSync(configPath, configContent);
console.log(`Created OpenAPI TypeScript config at: ${configPath}`);

// Update package.json scripts
const packageJsonPath = path.join(__dirname, '..', 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));

// Add type generation script if not exists
if (!packageJson.scripts['generate-types']) {
  packageJson.scripts['generate-types'] = 'openapi-ts';
  
  // Update dev and build scripts to generate types first
  const originalDev = packageJson.scripts.dev || 'next dev';
  const originalBuild = packageJson.scripts.build || 'next build';
  
  packageJson.scripts['dev:with-types'] = `npm run generate-types && ${originalDev}`;
  packageJson.scripts['build:with-types'] = `npm run generate-types && ${originalBuild}`;
  
  fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
  console.log('Updated package.json with type generation scripts');
}

// Create types directory if it doesn't exist
const typesDir = path.join(__dirname, '..', 'types', 'generated');
if (!fs.existsSync(typesDir)) {
  fs.mkdirSync(typesDir, { recursive: true });
  console.log(`Created types directory at: ${typesDir}`);
}

// Create a README for the generated types
const readmePath = path.join(typesDir, 'README.md');
const readmeContent = `# Generated TypeScript Types

This directory contains auto-generated TypeScript types from the backend OpenAPI schema.

## Generation

To regenerate types:

\`\`\`bash
npm run generate-types
\`\`\`

## Usage

Import types in your components:

\`\`\`typescript
import type { User, Project, ApiError } from '@/types/generated';
\`\`\`

**Note**: Do not manually edit files in this directory as they will be overwritten on regeneration.
`;

fs.writeFileSync(readmePath, readmeContent);
console.log('Created README for generated types');

console.log('\nSetup complete! To generate types:');
console.log('1. Make sure the backend is running at http://localhost:8000');
console.log('2. Run: npm install --save-dev @hey-api/openapi-ts');
console.log('3. Run: npm run generate-types');