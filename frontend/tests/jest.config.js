import path from 'path'
import nextJest from 'next/jest'

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
