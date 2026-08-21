interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = "Loading...", className = "" }: LoadingStateProps) {
  return (
    <div className={`flex h-64 items-center justify-center ${className}`}>
      <span className="text-sm text-muted-foreground animate-pulse">{message}</span>
    </div>
  );
}
