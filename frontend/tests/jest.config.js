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
    moduleNameMapper: {
        '^@/components/(.*)$': '<rootDir>/src/components/$1',
        '^@/pages/(.*)$': '<rootDir>/src/pages/$1',
        '^@/app/(.*)$': '<rootDir>/src/app/$1',
    },
}

export default createJestConfig(customJestConfig)
