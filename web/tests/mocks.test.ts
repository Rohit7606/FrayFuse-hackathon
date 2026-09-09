import { describe, test, expect } from 'vitest';
import Ajv from 'ajv';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load the JSON Schema
const schemaPath = path.resolve(__dirname, '../../schema.json');
const schemaContent = fs.readFileSync(schemaPath, 'utf8');
const schema = JSON.parse(schemaContent);

// @ts-ignore - Ajv constructor types can be tricky with ESM
const ajv = new Ajv({ strict: false });
// JSON schema draft 7 expects examples to be an array, but schema.json has an object.
delete schema.examples;
// Add the schema definitions
ajv.addSchema(schema, 'FrayFuseSchema');

describe('Mock Data Validation', () => {

  const validateMock = (mockName: string, definitionName: string) => {
    const mockPath = path.resolve(__dirname, `../src/mocks/${mockName}`);
    const mockContent = fs.readFileSync(mockPath, 'utf8');
    const mockData = JSON.parse(mockContent);

    const validate = ajv.getSchema(`FrayFuseSchema#/definitions/${definitionName}`);
    if (!validate) {
      throw new Error(`Schema definition ${definitionName} not found`);
    }

    const valid = validate(mockData);
    if (!valid) {
      console.error(validate.errors);
    }
    expect(valid).toBe(true);
  };

  test('test_mocks_valid', () => {
    validateMock('network.json', 'NetworkInput');
    validateMock('at-risk.json', 'AtRiskResponse');
    validateMock('simulate.json', 'ScoredNetwork');
    validateMock('intervene.json', 'InterveneResponse');
  });

});
