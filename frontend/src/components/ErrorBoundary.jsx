import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="max-w-xl w-full rounded-2xl border border-red-300 bg-white p-6 shadow-xl">
            <h2 className="font-display text-xl font-bold text-red-600">Đã xảy ra lỗi giao diện</h2>
            <p className="mt-2 text-sm text-gray-700 font-mono">
              {this.state.error?.toString()}
            </p>
            {this.state.errorInfo && (
              <pre className="mt-4 max-h-64 overflow-auto rounded bg-gray-100 p-3 text-xs text-gray-600">
                {this.state.error?.stack}
              </pre>
            )}
            <button
              onClick={() => {
                localStorage.clear();
                window.location.href = '/login';
              }}
              className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              Xóa cache & Đăng nhập lại
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
