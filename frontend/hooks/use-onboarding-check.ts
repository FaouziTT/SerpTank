import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { useProject } from '@/lib/project-context';

export function useOnboardingCheck() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAuth();
  const { organizations, isLoading } = useProject();

  useEffect(() => {
    // Don't check on auth pages or onboarding itself
    if (!user || isLoading || pathname.startsWith('/onboarding') || 
        pathname === '/login' || pathname === '/register') {
      return;
    }

    // Check if user has completed onboarding (has at least one organization)
    if (organizations.length === 0) {
      // Mark that we're redirecting to onboarding
      sessionStorage.setItem('onboarding_redirect', 'true');
      router.push('/onboarding');
    }
  }, [user, organizations, isLoading, pathname, router]);
}