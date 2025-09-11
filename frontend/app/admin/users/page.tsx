'use client';

import { useState, useEffect, useCallback } from 'react'; // <-- CHANGE #1: Import useCallback
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
  UserPlus, 
  MoreVertical, 
  Shield, 
  UserX,
  Mail,
  Calendar,
  Building2,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useToast } from '@/components/ui/use-toast';
import { User } from '@/types/api';

function AdminUsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // <-- CHANGE #2: Wrapped fetchUsers in useCallback
  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.users.list({ limit: 100 });
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      toast({
        title: 'Error',
        description: 'Failed to load users. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]); // Dependencies of the function itself

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]); // <-- CHANGE #3: Added fetchUsers to the dependency array

  const toggleUserStatus = async (userId: string, currentStatus: boolean) => {
    try {
      await api.users.updateUser(userId, { is_active: !currentStatus });
      toast({
        title: 'Success',
        description: `User ${currentStatus ? 'deactivated' : 'activated'} successfully.`,
      });
      fetchUsers();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update user status.',
        variant: 'destructive',
      });
    }
  };

  const toggleSuperuserStatus = async (userId: string, currentStatus: boolean) => {
    try {
      await api.users.updateUser(userId, { is_superuser: !currentStatus });
      toast({
        title: 'Success',
        description: `Admin privileges ${currentStatus ? 'removed' : 'granted'} successfully.`,
      });
      fetchUsers();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update admin privileges.',
        variant: 'destructive',
      });
    }
  };

  const filteredUsers = users.filter(user => 
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.full_name && user.full_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.username && user.username.toLowerCase().includes(searchTerm.toLowerCase()))
  );
  
  return (
    <AdminGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
              <p className="text-muted-foreground">
                Manage user accounts and permissions
              </p>
            </div>
            <Button>
              <UserPlus className="mr-2 h-4 w-4" />
              Add User
            </Button>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>All Users</CardTitle>
                  <CardDescription>
                    {filteredUsers.length} users total
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Organizations</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Joined</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{user.full_name || user.email}</span>
                            <span className="text-sm text-muted-foreground">{user.email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Building2 className="h-4 w-4 text-muted-foreground" />
                            <span>{user.organizations?.length || 0}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={user.is_active ? 'default' : 'secondary'}>
                            {user.is_active ? (
                              <>
                                <CheckCircle className="mr-1 h-3 w-3" />
                                Active
                              </>
                            ) : (
                              <>
                                <XCircle className="mr-1 h-3 w-3" />
                                Inactive
                              </>
                            )}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {user.is_superuser ? (
                            <Badge variant="destructive">
                              <Shield className="mr-1 h-3 w-3" />
                              Admin
                            </Badge>
                          ) : (
                            <Badge variant="outline">User</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            {new Date(user.created_at).toLocaleDateString()}
                          </div>
                        </TableCell>
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
                                <Mail className="mr-2 h-4 w-4" />
                                Send Email
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => toggleSuperuserStatus(user.id, user.is_superuser)}
                              >
                                <Shield className="mr-2 h-4 w-4" />
                                {user.is_superuser ? 'Remove Admin' : 'Make Admin'}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                className={user.is_active ? 'text-destructive' : ''}
                                onClick={() => toggleUserStatus(user.id, user.is_active)}
                              >
                                <UserX className="mr-2 h-4 w-4" />
                                {user.is_active ? 'Deactivate' : 'Activate'}
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

export default withAuth(AdminUsersPage);