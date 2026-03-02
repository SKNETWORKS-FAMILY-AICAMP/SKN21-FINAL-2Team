import '@testing-library/jest-dom'

// `jose` ships ESM-only entrypoints that Jest may not transform in this setup.
// For current tests we only need `decodeJwt`, so provide a minimal mock.
jest.mock('jose', () => ({
  decodeJwt: jest.fn(() => ({ exp: Math.floor(Date.now() / 1000) + 3600 })),
}))
