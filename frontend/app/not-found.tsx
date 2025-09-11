import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <h2 className="text-2xl mb-4">Page Not Found</h2>
      <p className="text-muted-foreground mb-8">The page you&apos;re looking for doesn&apos;t exist.</p>
      <Link href="/">
        <Button>Go Home</Button>
      </Link>
    </div>
  );
}