// Google Analytics gtag global interface
interface Window {
  gtag?: (
    command: 'config' | 'event' | 'js' | 'set',
    targetId: string,
    config?: Record<string, any>
  ) => void;
}