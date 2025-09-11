'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { AdminGuard } from '@/components/auth/admin-guard';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Search, 
  MoreVertical, 
  CreditCard,
  Calendar,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  DollarSign,
  Users,
  Activity
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { useToast } from '@/components/ui/use-toast';

interface Subscription {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  plan_name: string;
  status: 'active' | 'cancelled' | 'past_due' | 'trialing';
  amount: number;
  currency: string;
  billing_cycle: 'monthly' | 'yearly';
  current_period_start: string;
  current_period_end: string;
  created_at: string;
  trial_end?: string;
  cancel_at?: string;
  payment_method: string;
}

function AdminSubscriptionsPage() {
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch subscriptions with mock data
  const { data: subscriptions, isLoading, refetch } = useQuery({
    queryKey: ['admin-subscriptions'],
    queryFn: async () => {
      // Mock data - replace with actual API call when backend is ready
      const mockSubscriptions: Subscription[] = [
        {
          id: 'sub_1',
          user_id: 'user_1',
          user_email: 'john.doe@example.com',
          user_name: 'John Doe',
          plan_name: 'Pro',
          status: 'active',
          amount: 49.99,
          currency: 'USD',
          billing_cycle: 'monthly',
          current_period_start: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
          current_period_end: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
          payment_method: 'Visa •••• 4242'
        },
        {
          id: 'sub_2',
          user_id: 'user_2',
          user_email: 'jane.smith@example.com',
          user_name: 'Jane Smith',
          plan_name: 'Enterprise',
          status: 'active',
          amount: 199.99,
          currency: 'USD',
          billing_cycle: 'yearly',
          current_period_start: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString(),
          current_period_end: new Date(Date.now() + 185 * 24 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString(),
          payment_method: 'Mastercard •••• 5555'
        },
        {
          id: 'sub_3',
          user_id: 'user_3',
          user_email: 'bob.wilson@example.com',
          user_name: 'Bob Wilson',
          plan_name: 'Starter',
          status: 'past_due',
          amount: 19.99,
          currency: 'USD',
          billing_cycle: 'monthly',
          current_period_start: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
          current_period_end: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 120 * 24 * 60 * 60 * 1000).toISOString(),
          payment_method: 'Visa •••• 1234'
        },
        {
          id: 'sub_4',
          user_id: 'user_4',
          user_email: 'alice.johnson@example.com',
          user_name: 'Alice Johnson',
          plan_name: 'Pro',
          status: 'trialing',
          amount: 49.99,
          currency: 'USD',
          billing_cycle: 'monthly',
          current_period_start: new Date().toISOString(),
          current_period_end: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
          created_at: new Date().toISOString(),
          trial_end: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
          payment_method: 'Not set'
        }
      ];

      return mockSubscriptions;
    }
  });

  // Calculate metrics
  const metrics = subscriptions ? {
    total: subscriptions.length,
    active: subscriptions.filter(s => s.status === 'active').length,
    mrr: subscriptions
      .filter(s => s.status === 'active')
      .reduce((sum, s) => sum + (s.billing_cycle === 'monthly' ? s.amount : s.amount / 12), 0),
    churn: subscriptions.filter(s => s.status === 'cancelled').length / subscriptions.length * 100
  } : { total: 0, active: 0, mrr: 0, churn: 0 };

  const cancelSubscription = async (subscriptionId: string) => {
    try {
      // TODO: Implement actual API call
      toast({
        title: "Subscription cancelled",
        description: "The subscription has been marked for cancellation.",
      });
      refetch();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to cancel subscription",
      });
    }
  };

  const refundPayment = async (subscriptionId: string) => {
    try {
      // TODO: Implement actual API call
      toast({
        title: "Refund initiated",
        description: "The refund has been processed successfully.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to process refund",
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'cancelled':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'past_due':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'trialing':
        return <Activity className="h-4 w-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const filteredSubscriptions = subscriptions?.filter(sub => 
    sub.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sub.user_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sub.plan_name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <AdminGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Subscription Management</h1>
              <p className="text-muted-foreground">
                Monitor and manage user subscriptions
              </p>
            </div>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export Data
            </Button>
          </div>

          {/* Metrics Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Subscriptions</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.total}</div>
                <p className="text-xs text-muted-foreground">
                  {metrics.active} active
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly Recurring Revenue</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${metrics.mrr.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">
                  +12% from last month
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Churn Rate</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.churn.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">
                  -2% from last month
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Average Revenue</CardTitle>
                <CreditCard className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ${metrics.active > 0 ? (metrics.mrr / metrics.active).toFixed(2) : '0.00'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Per active subscription
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Subscriptions Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>All Subscriptions</CardTitle>
                  <CardDescription>
                    {filteredSubscriptions.length} subscriptions
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search subscriptions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Billing Period</TableHead>
                      <TableHead>Payment Method</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSubscriptions.map((subscription) => (
                      <TableRow key={subscription.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{subscription.user_name}</span>
                            <span className="text-sm text-muted-foreground">{subscription.user_email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{subscription.plan_name}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(subscription.status)}
                            <span className="capitalize">{subscription.status}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          ${subscription.amount}/{subscription.billing_cycle === 'monthly' ? 'mo' : 'yr'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            {new Date(subscription.current_period_end).toLocaleDateString()}
                          </div>
                        </TableCell>
                        <TableCell>{subscription.payment_method}</TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem>
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                Update Payment Method
                              </DropdownMenuItem>
                              {subscription.status === 'active' && (
                                <DropdownMenuItem 
                                  onClick={() => cancelSubscription(subscription.id)}
                                >
                                  Cancel Subscription
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                className="text-destructive"
                                onClick={() => refundPayment(subscription.id)}
                              >
                                Issue Refund
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </AdminGuard>
  );
}

export default withAuth(AdminSubscriptionsPage);