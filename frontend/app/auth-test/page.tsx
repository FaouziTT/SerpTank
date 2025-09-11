'use client';

import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useRouter } from 'next/navigation';

export default function AuthTestPage() {
  const { user, loading, error, logout } = useAuth();
  const router = useRouter();

  return (
    <div className="container mx-auto p-8">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Authentication Test Page</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold">Loading State:</h3>
            <p className="text-sm text-muted-foreground">{loading ? 'Loading...' : 'Not loading'}</p>
          </div>
          
          <div>
            <h3 className="font-semibold">User State:</h3>
            <pre className="text-sm bg-muted p-2 rounded">
              {user ? JSON.stringify(user, null, 2) : 'No user'}
            </pre>
          </div>
          
          <div>
            <h3 className="font-semibold">Error State:</h3>
            <p className="text-sm text-muted-foreground">{error || 'No error'}</p>
          </div>
          
          <div>
            <h3 className="font-semibold">LocalStorage Tokens:</h3>
            <pre className="text-sm bg-muted p-2 rounded">
              {typeof window !== 'undefined' 
                ? localStorage.getItem('serptank_tokens') || 'No tokens' 
                : 'Server-side rendering'}
            </pre>
          </div>
          
          <div className="flex gap-4">
            <Button onClick={() => router.push('/login')}>
              Go to Login
            </Button>
            <Button onClick={() => router.push('/dashboard')}>
              Go to Dashboard
            </Button>
            {user && (
              <Button onClick={logout} variant="destructive">
                Logout
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}