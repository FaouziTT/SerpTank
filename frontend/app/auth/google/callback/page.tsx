'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get the authorization code from URL
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        // Check for OAuth errors
        if (error) {
          throw new Error(errorDescription || `OAuth error: ${error}`);
        }

        if (!code) {
          throw new Error('No authorization code received');
        }

        // Exchange the authorization code for tokens
        // Use the correct POST endpoint for Google authentication
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google/authenticate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            code,
            redirect_uri: window.location.origin + '/auth/google/callback'
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to authenticate with Google');
        }

        const data = await response.json();

        // The backend should return tokens and user info
        // Store tokens and redirect to dashboard
        if (data.access_token) {
          // Use the auth context to handle the login
          await login(data.email || data.user.email, ''); // Google auth doesn't need password
          
          // Redirect to dashboard or the originally requested page
          const returnUrl = localStorage.getItem('authReturnUrl') || '/dashboard';
          localStorage.removeItem('authReturnUrl');
          router.push(returnUrl);
        } else {
          throw new Error('No access token received');
        }
      } catch (err) {
        console.error('Google OAuth callback error:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, router, login]);

  if (isProcessing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Completing Google Sign In</CardTitle>
            <CardDescription>Please wait while we complete your authentication...</CardDescription>
          </CardHeader>
          <CardContent>
            <LoadingState message="Authenticating with Google..." />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Authentication Failed</CardTitle>
            {/* CHANGE: Escaped the apostrophe in "couldn't" */}
            <CardDescription>We couldn&apos;t complete your Google sign in</CardDescription>
          </CardHeader>
          <CardContent>
            <ErrorState 
              error={error}
              onRetry={() => router.push('/login')}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingState message="Loading..." /></div>}>
      <GoogleCallbackContent />
    </Suspense>
  );
}