export default function LoadingSpinner({ className = '', label }) {
  return (
    <span className={`inline-flex items-center justify-center gap-2 ${className}`}>
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
        aria-hidden="true"
      />
      {label && <span>{label}</span>}
    </span>
  );
}
