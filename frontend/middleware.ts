import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Add routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/analytics',
  '/organizations',
  '/projects', 
  '/sites',
  '/monitoring',
  '/diagnostic',
  '/content-workflow',
  '/knowledge-engine',
  '/market-simulation',
  '/profitability',
  '/search-console',
  '/sge-readiness',
  '/settings',
  '/sessions',
  '/google-trends',
  '/youtube-analysis',
  '/serp-analysis',
  '/social-media',
  '/domains',
  '/audit-logs',
  '/team',
  '/billing',
];

// Add routes that should redirect to dashboard if already authenticated
const authRoutes = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  
  // Check if route requires authentication
  const isProtectedRoute = protectedRoutes.some(route => 
    path.startsWith(route) || path === route
  );
  
  // Check if user is trying to access auth routes
  const isAuthRoute = authRoutes.some(route => 
    path.startsWith(route) || path === route
  );
  
  // Get authentication status from cookie
  const hasAuth = request.cookies.get('serptank_has_auth')?.value === 'true';
  const accessToken = request.cookies.get('serptank_access_token')?.value;
  
  // Basic token validation (check if token exists and is not expired)
  let isValidToken = false;
  if (accessToken) {
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const now = Date.now() / 1000;
      isValidToken = payload.exp > now;
    } catch {
      isValidToken = false;
    }
  }
  
  // If accessing protected route without valid auth, redirect to login
  if (isProtectedRoute && (!hasAuth || !isValidToken)) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', path);
    return NextResponse.redirect(loginUrl);
  }
  
  // If accessing auth routes while authenticated, redirect to dashboard
  if (isAuthRoute && hasAuth && isValidToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).)',
  ],
};