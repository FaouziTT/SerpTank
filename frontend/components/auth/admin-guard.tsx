'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Loader2, ShieldAlert } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface AdminGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

export function AdminGuard({ children, fallback, redirectTo = '/dashboard' }: AdminGuardProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && !user.is_superuser && !fallback) {
      router.push(redirectTo);
    }
  }, [user, loading, router, redirectTo, fallback]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user || !user.is_superuser) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <ShieldAlert className="h-12 w-12 text-destructive" />
            </div>
            <CardTitle>Access Restricted</CardTitle>
            <CardDescription>
              This page requires administrator privileges. Please contact your system administrator if you believe you should have access.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Button onClick={() => router.push(redirectTo)}>
              Return to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

// HOC version for wrapping page components
export function withAdminAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: { fallback?: React.ReactNode; redirectTo?: string }
) {
  return function AdminProtectedComponent(props: P) {
    return (
      <AdminGuard {...options}>
        <Component {...props} />
      </AdminGuard>
    );
  };
}