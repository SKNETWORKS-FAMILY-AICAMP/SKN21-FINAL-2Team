import { render, screen, fireEvent } from '@testing-library/react'
import GoogleLoginBtn from '../src/components/GoogleLoginBtn'
import '@testing-library/jest-dom'

// Mock useRouter
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
}))

// Mock useGoogleLogin
const mockLogin = jest.fn()
jest.mock('@react-oauth/google', () => ({
    useGoogleLogin: (config: { onSuccess?: () => void }) => {
        if (config.onSuccess) config.onSuccess();
        return mockLogin
    },
}))

describe('GoogleLoginBtn', () => {
    it('renders login button', () => {
        render(<GoogleLoginBtn />)
        expect(screen.getByText('Login with Google')).toBeInTheDocument()
    })

    it('calls login function on click', () => {
        render(<GoogleLoginBtn />)
        const button = screen.getByRole('button')
        fireEvent.click(button)
        expect(mockLogin).toHaveBeenCalled()
    })
})
