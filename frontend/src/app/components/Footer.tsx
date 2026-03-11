export function Footer() {
    return (
        <footer className="bg-gray-950 text-gray-500 py-12 border-t border-gray-900">
            <div className="max-w-7xl mx-auto px-6 flex flex-col items-center justify-center gap-4 text-center">
                <p className="text-sm font-medium tracking-wide">
                    &copy; {new Date().getFullYear()} Triver. All rights reserved.
                </p>
            </div>
        </footer>
    );
}
