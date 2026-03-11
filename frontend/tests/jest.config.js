import path from 'path'
import { fileURLToPath } from 'url'
import nextJest from 'next/jest.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const createJestConfig = nextJest({
    dir: path.join(__dirname, '../'),
})

const customJestConfig = {
    rootDir: path.join(__dirname, '../'),
    setupFilesAfterEnv: ['<rootDir>/tests/jest.setup.js'],
    testEnvironment: 'jest-environment-jsdom',
    modulePathIgnorePatterns: ['<rootDir>/.next/'],
    testPathIgnorePatterns: ['<rootDir>/.next/'],
    watchPathIgnorePatterns: ['<rootDir>/.next/'],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
    },
}

export default createJestConfig(customJestConfig)
