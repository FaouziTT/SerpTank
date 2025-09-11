'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check if we're in the onboarding flow
    const isOnboarding = sessionStorage.getItem('onboarding_step') === 'google';
    
    // Check OAuth result
    const success = searchParams.get('success') === 'true';
    const error = searchParams.get('error');

    if (isOnboarding) {
      // Return to onboarding wizard
      if (success) {
        router.push('/onboarding?oauth_success=true');
      } else {
        router.push('/onboarding?oauth_error=' + (error || 'unknown'));
      }
    } else {
      // Regular OAuth flow - go to settings or dashboard
      if (success) {
        router.push('/settings?tab=integrations&oauth_success=true');
      } else {
        router.push('/settings?tab=integrations&oauth_error=' + (error || 'unknown'));
      }
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <h2 className="text-lg font-semibold">Processing authentication...</h2>
            <p className="text-sm text-muted-foreground">
              Please wait while we complete the connection.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
      <OAuthCallbackContent />
    </Suspense>
  );
}