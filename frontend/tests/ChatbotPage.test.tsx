import { render, screen } from '@testing-library/react'
import ChatbotPage from '../src/app/chatbot/page'
import '@testing-library/jest-dom'

// Mock useRouter
jest.mock('next/navigation', () => ({
    useRouter: () => ({
        push: jest.fn(),
    }),
}))

// Mock global fetch
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
    })
) as jest.Mock

describe('ChatbotPage', () => {
    it('renders chatbot interface', async () => {
        render(<ChatbotPage />)

        // Check for main elements
        expect(screen.getByPlaceholderText('메시지를 입력하세요...')).toBeInTheDocument()
        expect(screen.getByText('AI 챗봇과 대화하기')).toBeInTheDocument()
        expect(screen.getByText('전송')).toBeInTheDocument()
    })
})
