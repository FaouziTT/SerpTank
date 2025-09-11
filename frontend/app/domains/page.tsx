'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { AdminGuard } from '@/components/auth/admin-guard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
// import { Alert, AlertDescription } from '@/components/ui/alert'; // Component doesn't exist, using Card instead
import { 
  Globe,
  Plus,
  CheckCircle,
  XCircle,
  AlertCircle,
  Copy,
  ExternalLink,
  FileText,
  Code,
  Loader2,
  RefreshCw,
  Trash2
} from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { useToast } from '@/components/ui/use-toast';

interface Domain {
  id: string;
  domain: string;
  status: 'verified' | 'pending' | 'failed';
  verified_at: string | null;
  verification_method: 'dns' | 'html' | 'meta';
  verification_token: string;
  last_check: string;
}

function DomainsPage() {
  const { toast } = useToast();
  const [newDomain, setNewDomain] = useState('');
  const [selectedMethod, setSelectedMethod] = useState<'dns' | 'html' | 'meta'>('dns');

  // Fetch domains
  const { data: domains, isLoading, refetch } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => {
      try {
        const response = await api.domains.list();
        const domainList = response.data;
        
        // Transform backend data to match frontend interface
        return (domainList || []).map((domain: any) => ({
          id: domain.id || domain.domain_id,
          domain: domain.domain,
          status: domain.is_verified ? 'verified' : (domain.status || 'pending'),
          verified_at: domain.verified_at,
          verification_method: domain.verification_method || 'dns',
          verification_token: domain.verification_token || '',
          last_check: domain.last_check || domain.updated_at || new Date().toISOString()
        }));
      } catch (error) {
        console.error('Failed to fetch domains:', error);
        // Return empty array on error
        return [];
      }
    }
  });

  // Add domain mutation
  const addDomainMutation = useMutation({
    mutationFn: async (domain: string) => {
      // Use the initiateVerification endpoint to add a new domain
      return api.domains.initiateVerification({ 
        domain, 
        verification_method: selectedMethod 
      });
    },
    onSuccess: () => {
      toast({
        title: "Domain added",
        description: "Please complete the verification process.",
      });
      setNewDomain('');
      refetch();
    },
    onError: (error: any) => {
      toast({
        variant: "destructive",
        title: "Failed to add domain",
        description: error.response?.data?.detail || "Please check the domain and try again.",
      });
    }
  });

  // Verify domain mutation
  const verifyDomainMutation = useMutation({
    mutationFn: async (domainId: string) => {
      return api.domains.completeVerification({ 
        domain_id: domainId 
      });
    },
    onSuccess: () => {
      toast({
        title: "Verification check initiated",
        description: "Checking domain verification status...",
      });
      refetch();
    },
    onError: (error: any) => {
      toast({
        variant: "destructive",
        title: "Verification failed",
        description: error.response?.data?.detail || "Please check your verification settings.",
      });
    }
  });

  // Delete domain mutation
  const deleteDomainMutation = useMutation({
    mutationFn: async (domainId: string) => {
      return api.domains.delete(domainId);
    },
    onSuccess: () => {
      toast({
        title: "Domain removed",
        description: "The domain has been removed from your account.",
      });
      refetch();
    }
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied to clipboard",
      description: "The verification token has been copied.",
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getVerificationInstructions = (method: string, token: string) => {
    switch (method) {
      case 'dns':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Add a TXT record to your domain&apos;s DNS settings:
            </p>
            <div className="rounded-lg bg-muted p-4 font-mono text-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p><strong>Type:</strong> TXT</p>
                  <p><strong>Name:</strong> @</p>
                  <p><strong>Value:</strong> {token}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(token)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <Card className="border-yellow-200 bg-yellow-50">
              <CardContent className="flex items-start space-x-2 pt-4">
                <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                <p className="text-sm text-yellow-800">
                  DNS changes may take up to 48 hours to propagate.
                </p>
              </CardContent>
            </Card>
          </div>
        );
      case 'html':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Upload an HTML file to your website&apos;s root directory:
            </p>
            <div className="rounded-lg bg-muted p-4">
              <p className="font-mono text-sm mb-2">
                <strong>Filename:</strong> serptank-verification.html
              </p>
              <div className="font-mono text-sm bg-background p-3 rounded">
                {token}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => copyToClipboard(token)}
              >
                <Copy className="mr-2 h-4 w-4" />
                Copy content
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              The file should be accessible at: https://yourdomain.com/serptank-verification.html
            </p>
          </div>
        );
      case 'meta':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Add this meta tag to your homepage&apos;s &lt;head&gt; section:
            </p>
            <div className="rounded-lg bg-muted p-4">
              <code className="text-sm">
                &lt;meta name=&quot;serptank-verification&quot; content=&quot;{token}&quot; /&gt;
              </code>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 w-full"
                onClick={() => copyToClipboard(`<meta name="serptank-verification" content="${token}" />`)}
              >
                <Copy className="mr-2 h-4 w-4" />
                Copy meta tag
              </Button>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <AdminGuard>
      <DashboardLayout>
        <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Domain Management</h1>
          <p className="text-muted-foreground">
            Add and verify domains for SEO monitoring and analysis
          </p>
        </div>

        {/* Add New Domain */}
        <Card>
          <CardHeader>
            <CardTitle>Add New Domain</CardTitle>
            <CardDescription>
              Enter a domain to start monitoring its SEO performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex space-x-4">
                <div className="flex-1">
                  <Label htmlFor="domain" className="sr-only">Domain</Label>
                  <Input
                    id="domain"
                    placeholder="example.com"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                  />
                </div>
                <Button
                  onClick={() => addDomainMutation.mutate(newDomain)}
                  disabled={!newDomain || addDomainMutation.isPending}
                >
                  {addDomainMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  <Plus className="mr-2 h-4 w-4" />
                  Add Domain
                </Button>
              </div>
              <div className="space-y-2">
                <Label>Verification Method</Label>
                <div className="grid grid-cols-3 gap-4">
                  <Button
                    variant={selectedMethod === 'dns' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedMethod('dns')}
                  >
                    <Globe className="mr-2 h-4 w-4" />
                    DNS Record
                  </Button>
                  <Button
                    variant={selectedMethod === 'html' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedMethod('html')}
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    HTML File
                  </Button>
                  <Button
                    variant={selectedMethod === 'meta' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedMethod('meta')}
                  >
                    <Code className="mr-2 h-4 w-4" />
                    Meta Tag
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Domains List */}
        <Card>
          <CardHeader>
            <CardTitle>Your Domains</CardTitle>
            <CardDescription>
              Manage and verify your domains
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="space-y-4">
                {domains?.map((domain: any) => (
                  <div
                    key={domain.id}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium">{domain.domain}</h3>
                          <Badge
                            variant={
                              domain.status === 'verified' ? 'default' :
                              domain.status === 'pending' ? 'secondary' : 'destructive'
                            }
                          >
                            {getStatusIcon(domain.status)}
                            <span className="ml-1">{domain.status}</span>
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Verification method: {domain.verification_method.toUpperCase()}
                        </p>
                        {domain.verified_at && (
                          <p className="text-sm text-muted-foreground">
                            Verified on {new Date(domain.verified_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        {domain.status !== 'verified' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => verifyDomainMutation.mutate(domain.id)}
                          >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Check Verification
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(`https://${domain.domain}`, '_blank')}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteDomainMutation.mutate(domain.id)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                    
                    {domain.status !== 'verified' && (
                      <div className="mt-4">
                        <Tabs defaultValue="instructions" className="w-full">
                          <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="instructions">Instructions</TabsTrigger>
                            <TabsTrigger value="troubleshoot">Troubleshoot</TabsTrigger>
                          </TabsList>
                          <TabsContent value="instructions" className="mt-4">
                            {getVerificationInstructions(domain.verification_method, domain.verification_token)}
                          </TabsContent>
                          <TabsContent value="troubleshoot" className="mt-4">
                            <div className="space-y-4">
                              <Card className="border-yellow-200 bg-yellow-50">
                                <CardContent className="pt-4">
                                  <div className="flex items-start space-x-2">
                                    <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                                    <div className="text-sm text-yellow-800">
                                      <p className="font-semibold mb-2">Common issues:</p>
                                      <ul className="space-y-1">
                                        <li>• DNS propagation can take up to 48 hours</li>
                                        <li>• Ensure the verification file/tag is publicly accessible</li>
                                        <li>• Check for typos in the verification token</li>
                                        <li>• Verify you have the correct permissions to modify DNS/files</li>
                                      </ul>
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            </div>
                          </TabsContent>
                        </Tabs>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
    </AdminGuard>
  );
}

export default withAuth(DomainsPage);