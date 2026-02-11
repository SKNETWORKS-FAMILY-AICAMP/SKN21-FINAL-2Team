import GoogleLoginBtn from "@/components/GoogleLoginBtn";

export default function LoginPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center py-2">
            <main className="flex w-full flex-1 flex-col items-center justify-center px-20 text-center">
                <h1 className="text-4xl font-bold mb-8">
                    로그인
                </h1>
                <div className="flex flex-col items-center justify-center space-y-4">
                    <p className="text-lg">Google 계정으로 로그인하여 서비스를 이용하세요.</p>
                    <GoogleLoginBtn />
                </div>
            </main>
        </div>
    );
}
