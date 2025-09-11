'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  HelpCircle,
  Send,
  MessageSquare,
  Mail,
  Phone
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

function SupportPage() {
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const { toast } = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!subject || !description) {
      toast({
        title: 'Missing information',
        description: 'Please fill in all required fields.',
        variant: 'destructive',
      });
      return;
    }

    toast({
      title: 'Support request submitted',
      description: 'We\'ll respond to your request within 24 hours.',
    });

    setSubject('');
    setDescription('');
  };

  const supportContent = (
    <div className="space-y-8">
      {/* Contact Methods */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Live Chat
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              Chat with our support team
            </p>
            <Button variant="outline" className="w-full">Start Chat</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Email Support
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              support@serptank.com
            </p>
            <Button variant="outline" className="w-full">Send Email</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Phone Support
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              +1 (555) 123-4567
            </p>
            <Button variant="outline" className="w-full">Call Now</Button>
          </CardContent>
        </Card>
      </div>

      {/* Submit Ticket Form */}
      <Card>
        <CardHeader>
          <CardTitle>Submit a Support Ticket</CardTitle>
          <CardDescription>
            Describe your issue and we&apos;ll get back to you as soon as possible
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                placeholder="Brief description of your issue"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Please provide detailed information about your issue..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                required
              />
            </div>

            <Button type="submit" className="w-full">
              <Send className="mr-2 h-4 w-4" />
              Submit Ticket
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <DetailLayout
      title="Support Center"
      breadcrumbs={[
        { label: 'Help', href: '/help' },
        { label: 'Support' },
      ]}
      tabs={[
        {
          id: 'support',
          label: 'Support',
          icon: HelpCircle,
          content: supportContent,
        },
      ]}
    />
  );
}

export default withAuth(SupportPage);