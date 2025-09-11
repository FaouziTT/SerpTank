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
  AlertTriangle,
  Calendar,
  CheckCircle2,
  CreditCard,
  FileText,
  Gavel,
  Globe,
  Lock,
  Mail,
  MapPin,
  Scale,
  Shield,
  UserCheck,
  Users,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Terms sections with legal content
const termsSections = [
  {
    id: 'acceptance',
    title: 'Acceptance of Terms',
    icon: UserCheck,
    content: [
      {
        subtitle: 'Agreement to Terms',
        description: 'By accessing or using SerpTank services, you agree to be bound by these Terms of Service.',
        details: [
          'You must be at least 18 years old to use our services',
          'You represent that you have authority to bind your organization',
          'These terms constitute a legally binding agreement',
          'Continued use indicates acceptance of any updates',
          'You may not use our services if prohibited by law',
          'Violation of terms may result in service termination',
        ],
      },
      {
        subtitle: 'Modifications to Terms',
        description: 'We may update these terms from time to time to reflect changes in our services or legal requirements.',
        details: [
          'Updates will be posted on our website',
          'Material changes will be communicated via email',
          'Continued use after changes constitutes acceptance',
          'You may terminate your account if you disagree',
          'We will provide 30 days notice for material changes',
          'Previous versions are available upon request',
        ],
      },
      {
        subtitle: 'Capacity and Authority',
        description: 'You confirm that you have the legal capacity and authority to enter into this agreement.',
        details: [
          'You are legally authorized to bind your organization',
          'You have not been previously banned from our services',
          'All registration information is accurate and complete',
          'You will maintain accurate account information',
          'You are responsible for all account activity',
          'You will promptly notify us of unauthorized use',
        ],
      },
    ],
  },
  {
    id: 'service-description',
    title: 'Service Description',
    icon: Zap,
    content: [
      {
        subtitle: 'Platform Services',
        description: 'SerpTank provides AI-powered SEO analytics, monitoring, and optimization tools.',
        details: [
          'Real-time website performance monitoring',
          'SEO analytics and reporting dashboards',
          'Keyword tracking and ranking analysis',
          'Competitive intelligence and insights',
          'Content optimization recommendations',
          'Technical SEO audit capabilities',
        ],
      },
      {
        subtitle: 'Service Availability',
        description: 'We strive to maintain high service availability but cannot guarantee uninterrupted access.',
        details: [
          'Target 99.9% uptime service level agreement',
          'Planned maintenance windows with advance notice',
          'Emergency maintenance may occur without notice',
          'Service credits for extended outages',
          'No guarantee of continuous availability',
          'Third-party integrations may affect availability',
        ],
      },
      {
        subtitle: 'Feature Updates',
        description: 'We continuously improve our platform by adding new features and capabilities.',
        details: [
          'New features may be added to existing plans',
          'Some features may require plan upgrades',
          'Beta features may have limited availability',
          'Features may be modified or discontinued',
          'We will notify users of significant changes',
          'Feedback is welcome for feature development',
        ],
      },
    ],
  },
  {
    id: 'user-accounts',
    title: 'User Accounts and Responsibilities',
    icon: Users,
    content: [
      {
        subtitle: 'Account Registration',
        description: 'Creating an account requires accurate information and agreement to these terms.',
        details: [
          'Provide accurate and complete registration information',
          'Choose a secure password and protect your credentials',
          'You are responsible for all account activity',
          'Notify us immediately of unauthorized access',
          'One person may not maintain multiple accounts',
          'Business accounts require appropriate authorization',
        ],
      },
      {
        subtitle: 'Acceptable Use',
        description: 'You must use our services in accordance with applicable laws and these terms.',
        details: [
          'Comply with all applicable laws and regulations',
          'Respect intellectual property rights',
          'Do not interfere with service operation',
          'No unauthorized access to other accounts',
          'No transmission of harmful or illegal content',
          'Report suspected violations to our team',
        ],
      },
      {
        subtitle: 'Account Termination',
        description: 'Either party may terminate the account relationship under certain circumstances.',
        details: [
          'You may cancel your account at any time',
          'We may suspend accounts for terms violations',
          'Immediate termination for severe violations',
          '30-day notice for non-payment termination',
          'Data export available before termination',
          'No refunds for terminated accounts',
        ],
      },
    ],
  },
  {
    id: 'payment-billing',
    title: 'Payment and Billing',
    icon: CreditCard,
    content: [
      {
        subtitle: 'Subscription Plans',
        description: 'Our services are provided on a subscription basis with various pricing tiers.',
        details: [
          'Monthly and annual billing options available',
          'Pricing is displayed in USD unless otherwise noted',
          'Plan features and limits are clearly defined',
          'Upgrade or downgrade anytime during billing period',
          'Unused features do not carry over between periods',
          'Educational and non-profit discounts may apply',
        ],
      },
      {
        subtitle: 'Payment Processing',
        description: 'Payments are processed securely through our third-party payment providers.',
        details: [
          'Payments automatically charged on billing date',
          'Valid payment method required for account activation',
          'We do not store complete credit card information',
          'Failed payments may result in service suspension',
          'Update payment information to avoid interruption',
          'Payment disputes handled through provider',
        ],
      },
      {
        subtitle: 'Refund Policy',
        description: 'We offer refunds under specific circumstances outlined in our policy.',
        details: [
          '14-day money-back guarantee for new customers',
          'Refunds processed within 5-10 business days',
          'No refunds for accounts terminated for violations',
          'Partial refunds not available for monthly plans',
          'Annual plans may receive prorated refunds',
          'Contact support for refund requests',
        ],
      },
    ],
  },
  {
    id: 'intellectual-property',
    title: 'Intellectual Property',
    icon: Shield,
    content: [
      {
        subtitle: 'Our Rights',
        description: 'SerpTank and its licensors own all rights to the platform, software, and related materials.',
        details: [
          'All platform software and code are proprietary',
          'Trademarks and logos are owned by SerpTank',
          'Documentation and help materials are copyrighted',
          'No rights granted except as explicitly stated',
          'Reverse engineering is strictly prohibited',
          'Third-party components retain their respective licenses',
        ],
      },
      {
        subtitle: 'Your Content',
        description: 'You retain ownership of your data while granting us necessary rights to provide services.',
        details: [
          'You own all data you upload to our platform',
          'Grant us license to process data for service delivery',
          'You are responsible for lawful use of your data',
          'Ensure you have rights to all uploaded content',
          'We may aggregate anonymized data for analytics',
          'Your data rights are detailed in our Privacy Policy',
        ],
      },
      {
        subtitle: 'DMCA Compliance',
        description: 'We respond to valid copyright infringement notices under the Digital Millennium Copyright Act.',
        details: [
          'Submit takedown notices to our designated agent',
          'Include all required DMCA elements in notices',
          'We will investigate and respond promptly',
          'Counter-notifications accepted for disputed claims',
          'Repeat infringers may have accounts terminated',
          'Good faith belief required for all notices',
        ],
      },
    ],
  },
  {
    id: 'limitations-liability',
    title: 'Limitations of Liability',
    icon: AlertTriangle,
    content: [
      {
        subtitle: 'Service Disclaimers',
        description: 'Our services are provided on an "as is" basis without warranties of any kind.',
        details: [
          'No warranty of uninterrupted or error-free operation',
          'Accuracy of SEO data depends on third-party sources',
          'Results may vary based on website and market factors',
          'We disclaim all express and implied warranties',
          'No guarantee of specific business outcomes',
          'User assumes all risks of service use',
        ],
      },
      {
        subtitle: 'Limitation of Damages',
        description: 'Our liability is limited to the maximum extent permitted by applicable law.',
        details: [
          'Liability limited to amount paid in preceding 12 months',
          'No liability for indirect or consequential damages',
          'No liability for lost profits or business opportunities',
          'Exclusions apply even if we have been advised of possibility',
          'Some jurisdictions may not allow liability limitations',
          'User responsible for backup and security measures',
        ],
      },
      {
        subtitle: 'Force Majeure',
        description: 'We are not liable for failures due to circumstances beyond our reasonable control.',
        details: [
          'Natural disasters and acts of government',
          'Internet or telecommunications failures',
          'Third-party service provider outages',
          'Cyber attacks and security breaches',
          'Labor disputes and supply chain disruptions',
          'Other events beyond our reasonable control',
        ],
      },
    ],
  },
  {
    id: 'dispute-resolution',
    title: 'Dispute Resolution',
    icon: Gavel,
    content: [
      {
        subtitle: 'Informal Resolution',
        description: 'We encourage resolving disputes through direct communication before formal proceedings.',
        details: [
          'Contact our support team for assistance',
          'Provide detailed description of the issue',
          'Allow 30 days for good faith resolution efforts',
          'Escalation to management for complex disputes',
          'Documentation of resolution attempts may be required',
          'Most disputes can be resolved informally',
        ],
      },
      {
        subtitle: 'Binding Arbitration',
        description: 'Unresolved disputes will be settled through binding arbitration.',
        details: [
          'Arbitration conducted under American Arbitration Association rules',
          'Single arbitrator selected by mutual agreement',
          'Arbitration location in San Francisco, California',
          'Each party bears their own costs and fees',
          'Arbitrator decision is final and binding',
          'Class actions and jury trials are waived',
        ],
      },
      {
        subtitle: 'Governing Law',
        description: 'These terms are governed by the laws of the State of California.',
        details: [
          'California state law governs interpretation',
          'Federal laws apply where applicable',
          'Venue in San Francisco County courts',
          'Choice of law rules do not apply',
          'UN Convention on Contracts excluded',
          'Local laws may provide additional protections',
        ],
      },
    ],
  },
];

// Legal contact information
const legalContact = {
  officer: 'Sarah Chen',
  title: 'Legal Counsel',
  email: 'legal@serptank.com',
  address: 'SerpTank Inc., 123 Mission Street, San Francisco, CA 94105',
  phone: '+1 (555) 123-4567',
};

// Terms update history
const termsUpdates = [
  {
    date: 'January 15, 2025',
    description: 'Updated payment terms and refund policy clarifications',
    type: 'minor',
  },
  {
    date: 'October 1, 2024',
    description: 'Major revision including new liability limitations and arbitration clauses',
    type: 'major',
  },
  {
    date: 'July 1, 2024',
    description: 'Added clauses for AI data processing and new feature releases',
    type: 'minor',
  },
  {
    date: 'March 15, 2024',
    description: 'Initial Terms of Service publication',
    type: 'initial',
  },
];

export default function TermsPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState('acceptance');
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
      
      // Update active section based on scroll position
      const sections = termsSections.map(section => {
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
          <SEOOrb className="scale-150" colorTheme="orange" />
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
              <Scale className="mr-1 h-3 w-3" />
              Terms of Service
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Clear Terms,</span>
            <span className="block text-gradient-electric mt-2">Fair Usage</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            These terms govern your use of SerpTank services. We believe in transparency
            and fair treatment for all our users and customers.
          </motion.p>

          <motion.div 
            className="flex items-center justify-center gap-6 text-sm text-muted-foreground"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span>Effective: January 15, 2025</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span>Governed by California Law</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Terms Content with Sidebar Navigation */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-4 gap-12">
            {/* Sticky Sidebar Navigation */}
            <div className="lg:col-span-1">
              <div className="sticky top-32">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-6">
                  Terms Sections
                </h3>
                <nav className="space-y-2">
                  {termsSections.map((section) => (
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

                {/* Legal Contact Info Card */}
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
                        <span>Legal Questions?</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 text-sm">
                        <div>
                          <div className="font-medium">{legalContact.officer}</div>
                          <div className="text-muted-foreground">{legalContact.title}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Mail className="h-4 w-4 text-accent" />
                          <a href={`mailto:${legalContact.email}`} className="text-accent hover:underline">
                            {legalContact.email}
                          </a>
                        </div>
                        <div className="flex items-start space-x-2">
                          <MapPin className="h-4 w-4 text-accent mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">{legalContact.address}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Important Notice */}
                <motion.div 
                  className="mt-6"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                >
                  <Card className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20">
                    <CardContent className="p-4">
                      <div className="flex items-start space-x-3">
                        <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
                        <div className="space-y-2">
                          <div className="font-medium text-amber-200">Important Notice</div>
                          <p className="text-sm text-muted-foreground">
                            These terms include binding arbitration and class action waiver provisions.
                            Please read carefully.
                          </p>
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
                {termsSections.map((section, sectionIndex) => (
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

                {/* Terms Updates History */}
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
                      <h2 className="text-3xl font-bold">Terms Update History</h2>
                      <p className="text-muted-foreground mt-2">Track changes to our terms of service over time</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {termsUpdates.map((update, index) => (
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
            Ready to Get <span className="text-gradient-electric">Started</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            By using our services, you agree to these terms. Questions? Our team is here to help.
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => router.push('/register')}
              >
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="glass"
                size="xl"
                onClick={() => window.open(`mailto:${legalContact.email}`, '_blank')}
                className="text-xl"
                magneticStrength={0}
              >
                Contact Legal Team
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
              <Link href="/privacy" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm text-foreground font-medium">
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