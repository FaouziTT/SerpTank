'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  Cookie,
  Database,
  Eye,
  FileText,
  Globe,
  Lock,
  Mail,
  MapPin,
  Shield,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Privacy sections with GDPR compliance
const privacySections = [
  {
    id: 'information-collection',
    title: 'Information We Collect',
    icon: Database,
    content: [
      {
        subtitle: 'Personal Information',
        description: 'We collect information you provide directly to us when you create an account, use our services, or contact us.',
        details: [
          'Name and email address',
          'Company name and job title',
          'Website URLs and domain information',
          'Payment and billing information',
          'Communication preferences',
          'Support inquiries and feedback',
        ],
      },
      {
        subtitle: 'Usage Information',
        description: 'We automatically collect information about how you use our platform.',
        details: [
          'SEO data and website analytics',
          'Feature usage patterns',
          'Device and browser information',
          'IP address and location data',
          'Session duration and activity logs',
          'Performance metrics',
        ],
      },
      {
        subtitle: 'Third-Party Integrations',
        description: 'When you connect external services, we may collect data from those platforms.',
        details: [
          'Google Search Console data',
          'Google Analytics information',
          'Social media metrics',
          'Advertising platform data',
          'CRM system integrations',
          'Third-party tool connections',
        ],
      },
    ],
  },
  {
    id: 'use-of-information',
    title: 'How We Use Your Information',
    icon: Zap,
    content: [
      {
        subtitle: 'Service Provision',
        description: 'We use your information to provide, maintain, and improve our SEO platform.',
        details: [
          'Deliver SEO insights and recommendations',
          'Generate reports and analytics',
          'Monitor website performance',
          'Provide customer support',
          'Process payments and billing',
          'Send service-related notifications',
        ],
      },
      {
        subtitle: 'Product Enhancement',
        description: 'We analyze usage patterns to enhance our platform and develop new features.',
        details: [
          'Improve AI algorithms and predictions',
          'Develop new SEO capabilities',
          'Optimize user experience',
          'Conduct A/B testing',
          'Fix bugs and technical issues',
          'Create industry benchmarks',
        ],
      },
      {
        subtitle: 'Communication',
        description: 'We may use your information to communicate with you about our services.',
        details: [
          'Account and security notifications',
          'Product updates and announcements',
          'Educational content and resources',
          'Marketing communications (with consent)',
          'Customer satisfaction surveys',
          'Legal and compliance notices',
        ],
      },
    ],
  },
  {
    id: 'data-sharing',
    title: 'Information Sharing and Disclosure',
    icon: Users,
    content: [
      {
        subtitle: 'Service Providers',
        description: 'We share information with trusted third parties who help us operate our platform.',
        details: [
          'Cloud hosting and infrastructure providers',
          'Payment processing companies',
          'Customer support platforms',
          'Analytics and monitoring services',
          'Email delivery services',
          'Security and compliance vendors',
        ],
      },
      {
        subtitle: 'Business Transfers',
        description: 'Information may be transferred in connection with business transactions.',
        details: [
          'Mergers and acquisitions',
          'Asset sales or transfers',
          'Corporate restructuring',
          'Bankruptcy proceedings',
          'Due diligence processes',
          'Investment or financing activities',
        ],
      },
      {
        subtitle: 'Legal Requirements',
        description: 'We may disclose information when required by law or to protect our rights.',
        details: [
          'Legal process and court orders',
          'Government requests and investigations',
          'Regulatory compliance requirements',
          'Protection of rights and property',
          'Public safety and security',
          'Prevention of fraud and abuse',
        ],
      },
    ],
  },
  {
    id: 'data-security',
    title: 'Data Security',
    icon: ShieldCheck,
    content: [
      {
        subtitle: 'Technical Safeguards',
        description: 'We implement industry-standard security measures to protect your data.',
        details: [
          'End-to-end encryption in transit',
          'AES-256 encryption at rest',
          'Multi-factor authentication',
          'Regular security audits',
          'Penetration testing',
          'Intrusion detection systems',
        ],
      },
      {
        subtitle: 'Administrative Controls',
        description: 'We maintain strict access controls and employee training programs.',
        details: [
          'Role-based access permissions',
          'Background checks for employees',
          'Data handling training programs',
          'Incident response procedures',
          'Regular compliance reviews',
          'Third-party security assessments',
        ],
      },
      {
        subtitle: 'Compliance Certifications',
        description: 'We maintain various security and compliance certifications.',
        details: [
          'SOC 2 Type II certification',
          'ISO 27001 compliance',
          'GDPR compliance framework',
          'CCPA compliance measures',
          'PCI DSS for payment data',
          'Regular third-party audits',
        ],
      },
    ],
  },
  {
    id: 'your-rights',
    title: 'Your Privacy Rights',
    icon: Eye,
    content: [
      {
        subtitle: 'Data Access Rights',
        description: 'You have the right to access and control your personal information.',
        details: [
          'Request copies of your data',
          'View data processing activities',
          'Download your information',
          'Verify data accuracy',
          'Understand data sources',
          'Review automated processing',
        ],
      },
      {
        subtitle: 'Data Control Rights',
        description: 'You can modify, restrict, or delete your personal information.',
        details: [
          'Update account information',
          'Correct inaccurate data',
          'Delete your account',
          'Restrict data processing',
          'Object to certain uses',
          'Withdraw consent',
        ],
      },
      {
        subtitle: 'Portability and Deletion',
        description: 'You can request data portability or complete deletion of your information.',
        details: [
          'Export data in machine-readable format',
          'Transfer data to other services',
          'Complete account deletion',
          'Erasure of personal information',
          'Right to be forgotten',
          'Data retention management',
        ],
      },
    ],
  },
  {
    id: 'cookies-tracking',
    title: 'Cookies and Tracking',
    icon: Cookie,
    content: [
      {
        subtitle: 'Essential Cookies',
        description: 'Necessary cookies that enable core platform functionality.',
        details: [
          'Authentication and session management',
          'Security and fraud prevention',
          'Load balancing and performance',
          'User preferences and settings',
          'Shopping cart and checkout',
          'Legal compliance tracking',
        ],
      },
      {
        subtitle: 'Analytics Cookies',
        description: 'Help us understand how users interact with our platform.',
        details: [
          'Page views and user journeys',
          'Feature usage statistics',
          'Performance monitoring',
          'Error tracking and debugging',
          'A/B testing and optimization',
          'User behavior analysis',
        ],
      },
      {
        subtitle: 'Marketing Cookies',
        description: 'Used to deliver relevant advertising and marketing content.',
        details: [
          'Targeted advertising campaigns',
          'Social media integration',
          'Conversion tracking',
          'Retargeting and remarketing',
          'Cross-platform attribution',
          'Campaign effectiveness measurement',
        ],
      },
    ],
  },
];

// Contact information for privacy inquiries
const privacyContact = {
  officer: 'Jennifer Park',
  title: 'Data Protection Officer',
  email: 'privacy@serptank.com',
  address: 'SerpTank Inc., 123 Mission Street, San Francisco, CA 94105',
  phone: '+1 (555) 123-4567',
};

// Key dates and updates
const privacyUpdates = [
  {
    date: 'January 15, 2025',
    description: 'Updated data retention policies and cookie management',
    type: 'minor',
  },
  {
    date: 'October 1, 2024',
    description: 'Enhanced GDPR compliance and user rights section',
    type: 'major',
  },
  {
    date: 'July 1, 2024',
    description: 'Added information about AI data processing',
    type: 'minor',
  },
  {
    date: 'March 15, 2024',
    description: 'Initial privacy policy publication',
    type: 'initial',
  },
];

export default function PrivacyPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState('information-collection');
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
      
      // Update active section based on scroll position
      const sections = privacySections.map(section => {
        const element = document.getElementById(section.id);
        if (element) {
          const rect = element.getBoundingClientRect();
          return {
            id: section.id,
            top: rect.top,
            height: rect.height,
          };
        }
        return null;
      }).filter(Boolean);

      const current = sections.find(section => 
        section && section.top <= 200 && section.top + section.height > 200
      );

      if (current) {
        setActiveSection(current.id);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground relative noise-overlay">
      
      {/* Modern Navigation */}
      <nav className={`fixed top-0 w-full z-50 transition-all duration-500 ${
        isScrolled 
          ? 'bg-background/80 backdrop-blur-xl border-b border-border' 
          : 'bg-transparent'
      }`}>
        <div className="container-width px-6 mx-auto">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-12">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="relative w-10 h-10">
                  <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={40} height={40} className="w-full h-full object-contain" />
                </div>
                <span className="text-2xl font-bold tracking-tight">SerpTank</span>
              </Link>
              <div className="hidden lg:flex items-center space-x-8">
                {['Features', 'Pricing', 'Case Studies', 'About'].map((item) => (
                  <Link
                    key={item}
                    href={`/${item.toLowerCase().replace(' ', '-')}`}
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                  >
                    {item}
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                  </Link>
                ))}
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <SimpleMagneticWrapper>
                <MagneticButton
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/login')}
                  magneticStrength={0}
                >
                  Sign In
                </MagneticButton>
              </SimpleMagneticWrapper>
              <SimpleMagneticWrapper>
                <CTAButton
                  size="sm"
                  onClick={() => router.push('/register')}
                >
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4" />
                </CTAButton>
              </SimpleMagneticWrapper>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section with Parallax */}
      <section className="relative min-h-[60vh] flex items-center justify-center overflow-hidden pt-20">
        {/* Background gradient mesh */}
        <motion.div 
          className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10"
          style={{ y: meshY }}
        />
        
        {/* Enhanced floating 3D orb */}
        <motion.div
          className="absolute right-[-200px] top-1/2 -translate-y-1/2 w-[800px] h-[800px] lg:w-[1000px] lg:h-[1000px]"
          style={{ y: heroY, scale: orbScale }}
        >
          <SEOOrb className="scale-150" colorTheme="purple" />
        </motion.div>
        
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <motion.div
            className="absolute -top-32 -left-32 w-64 h-64 bg-primary/20 rounded-full blur-3xl"
            animate={{
              x: [0, 100, 0],
              y: [0, -50, 0],
            }}
            transition={{
              duration: 20,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
          <motion.div
            className="absolute -bottom-32 -right-32 w-96 h-96 bg-accent/20 rounded-full blur-3xl"
            animate={{
              x: [0, -100, 0],
              y: [0, 50, 0],
            }}
            transition={{
              duration: 25,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        </div>
        
        <motion.div 
          className="container-width px-6 mx-auto text-center relative z-10"
          style={{ y: heroY }}
        >
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <Badge variant="secondary" className="mb-6 animate-slide-up-fade">
              <Shield className="mr-1 h-3 w-3" />
              Privacy Policy
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Your Privacy</span>
            <span className="block text-gradient-electric mt-2">Matters to Us</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            We are committed to protecting your personal information and your right to privacy.
            This policy explains how we collect, use, and safeguard your data.
          </motion.p>

          <motion.div 
            className="flex items-center justify-center gap-6 text-sm text-muted-foreground"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span>Last Updated: January 15, 2025</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span>GDPR Compliant</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Privacy Content with Sidebar Navigation */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-4 gap-12">
            {/* Sticky Sidebar Navigation */}
            <div className="lg:col-span-1">
              <div className="sticky top-32">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-6">
                  Privacy Sections
                </h3>
                <nav className="space-y-2">
                  {privacySections.map((section) => (
                    <button
                      key={section.id}
                      onClick={() => scrollToSection(section.id)}
                      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 text-left ${
                        activeSection === section.id
                          ? 'bg-primary/10 text-primary border-l-4 border-primary'
                          : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
                      }`}
                    >
                      <section.icon className={`h-5 w-5 flex-shrink-0 ${
                        activeSection === section.id ? 'text-primary' : 'text-muted-foreground'
                      }`} />
                      <div>
                        <div className="font-medium text-sm">{section.title}</div>
                        {activeSection === section.id && (
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {section.content.length} subsections
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </nav>

                {/* Contact Info Card */}
                <motion.div 
                  className="mt-8"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                >
                  <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-lg">
                        <Mail className="h-5 w-5 text-primary" />
                        <span>Privacy Questions?</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 text-sm">
                        <div>
                          <div className="font-medium">{privacyContact.officer}</div>
                          <div className="text-muted-foreground">{privacyContact.title}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Mail className="h-4 w-4 text-accent" />
                          <a href={`mailto:${privacyContact.email}`} className="text-accent hover:underline">
                            {privacyContact.email}
                          </a>
                        </div>
                        <div className="flex items-start space-x-2">
                          <MapPin className="h-4 w-4 text-accent mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">{privacyContact.address}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              <div className="space-y-16">
                {privacySections.map((section, sectionIndex) => (
                  <motion.div
                    key={section.id}
                    id={section.id}
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: sectionIndex * 0.1 }}
                  >
                    {/* Section Header */}
                    <div className="flex items-center space-x-4 mb-8">
                      <div className="p-3 rounded-lg bg-primary/10">
                        <section.icon className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h2 className="text-3xl font-bold">{section.title}</h2>
                      </div>
                    </div>

                    {/* Section Content */}
                    <div className="space-y-8">
                      {section.content.map((subsection, subsectionIndex) => (
                        <motion.div
                          key={subsectionIndex}
                          initial={{ opacity: 0, x: -20 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.5, delay: subsectionIndex * 0.1 }}
                        >
                          <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                            <CardHeader>
                              <CardTitle className="text-xl">{subsection.subtitle}</CardTitle>
                              <CardDescription className="text-base">
                                {subsection.description}
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              <ul className="space-y-3">
                                {subsection.details.map((detail, detailIndex) => (
                                  <motion.li 
                                    key={detailIndex}
                                    className="flex items-start space-x-3"
                                    initial={{ opacity: 0, x: -20 }}
                                    whileInView={{ opacity: 1, x: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: detailIndex * 0.05 }}
                                  >
                                    <CheckCircle2 className="h-5 w-5 text-accent mt-0.5 flex-shrink-0" />
                                    <span>{detail}</span>
                                  </motion.li>
                                ))}
                              </ul>
                            </CardContent>
                          </Card>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                ))}

                {/* Policy Updates History */}
                <motion.div
                  initial={{ opacity: 0, y: 50 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                  className="mt-16"
                >
                  <div className="flex items-center space-x-4 mb-8">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <FileText className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-3xl font-bold">Policy Update History</h2>
                      <p className="text-muted-foreground mt-2">Track changes to our privacy policy over time</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {privacyUpdates.map((update, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                          <CardContent className="p-6">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-4">
                                <Badge 
                                  variant={update.type === 'major' ? 'default' : update.type === 'initial' ? 'destructive' : 'secondary'}
                                >
                                  {update.type === 'major' ? 'Major Update' : update.type === 'initial' ? 'Initial' : 'Minor Update'}
                                </Badge>
                                <span className="font-medium">{update.date}</span>
                              </div>
                            </div>
                            <p className="text-muted-foreground mt-2">{update.description}</p>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* CTA Section */}
      <section className="relative section-padding overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-accent/5 to-destructive/5" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,hsl(var(--background))_50%)]" />
        </div>
        
        <motion.div
          className="container-width px-6 mx-auto text-center relative z-10"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
            Questions About <span className="text-gradient-electric">Your Privacy</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Our team is here to help you understand how we protect and use your data
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => window.open(`mailto:${privacyContact.email}`, '_blank')}
              >
                Contact Privacy Team
                <ArrowRight className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="glass"
                size="xl"
                onClick={() => router.push('/support')}
                className="text-xl"
                magneticStrength={0}
              >
                Get Support
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Modern Footer */}
      <footer className="relative py-16 border-t border-border bg-gray-50/40 dark:bg-gray-950/40">
        <div className="container-width px-6 mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12 mb-12">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-6">
                <div className="relative w-8 h-8">
                  <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={32} height={32} className="w-full h-full object-contain" />
                </div>
                <span className="text-2xl font-bold">SerpTank</span>
              </div>
              <p className="text-muted-foreground mb-6 max-w-xs leading-relaxed">
                The AI-powered SEO platform that delivers real business results.
              </p>
              <div className="flex space-x-4">
                {[
                  { name: 'twitter', icon: 'X' },
                  { name: 'linkedin', icon: 'in' },
                  { name: 'github', icon: 'G' }
                ].map((social) => (
                  <a
                    key={social.name}
                    href={`https://${social.name}.com/serptank`}
                    className="w-10 h-10 rounded-full bg-card border border-border flex items-center justify-center hover:bg-primary/10 hover:border-primary/50 transition-all group"
                  >
                    <span className="sr-only">{social.name}</span>
                    <span className="text-sm font-bold text-muted-foreground group-hover:text-primary transition-colors">
                      {social.icon}
                    </span>
                  </a>
                ))}
              </div>
            </div>
            
            {[
              { title: 'Product', links: ['Features', 'Pricing', 'Changelog', 'Roadmap'] },
              { title: 'Company', links: ['About', 'Blog', 'Careers', 'Press'] },
              { title: 'Resources', links: ['Documentation', 'API', 'Status', 'Support'] },
            ].map((column, index) => (
              <div key={index}>
                <h3 className="font-semibold mb-4">{column.title}</h3>
                <ul className="space-y-2">
                  {column.links.map((link) => (
                    <li key={link}>
                      <Link
                        href={`/${link.toLowerCase()}`}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {link}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          
          <div className="border-t border-border pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-muted-foreground order-2 md:order-1">
              © 2025 SerpTank. All rights reserved.
            </p>
            <div className="flex flex-wrap justify-center gap-6 order-1 md:order-2">
              <Link href="/privacy" className="text-sm text-foreground font-medium">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="/security" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Security
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}