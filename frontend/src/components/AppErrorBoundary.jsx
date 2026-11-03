import React from 'react';

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('KiranaSync render error:', error, info);
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="min-h-screen bg-slate-950 p-6 text-white">
        <div className="mx-auto max-w-3xl rounded-xl border border-red-400 bg-red-950 p-5">
          <h1 className="text-xl font-bold">KiranaSync could not render</h1>
          <pre className="mt-4 whitespace-pre-wrap break-words rounded bg-black/40 p-4 text-sm text-red-100">
            {this.state.error?.stack || this.state.error?.message || String(this.state.error)}
          </pre>
        </div>
      </div>
    );
  }
}
