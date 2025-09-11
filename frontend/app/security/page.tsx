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
  AlertCircle,
  Calendar,
  CheckCircle2,
  Cloud,
  Database,
  Eye,
  FileCheck,
  Globe,
  Key,
  Lock,
  Mail,
  Monitor,
  Network,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Security framework sections
const securitySections = [
  {
    id: 'data-protection',
    title: 'Data Protection & Encryption',
    icon: Lock,
    content: [
      {
        subtitle: 'Encryption at Rest',
        description: 'All customer data is encrypted using industry-standard AES-256 encryption when stored in our databases.',
        details: [
          'AES-256 encryption for all customer data',
          'Encrypted database volumes and file systems',
          'Hardware security modules for key management',
          'Regular encryption key rotation policies',
          'Secure key storage and access controls',
          'Third-party encryption audits and validation',
        ],
      },
      {
        subtitle: 'Encryption in Transit',
        description: 'Data transmitted between clients and our servers is protected using TLS encryption.',
        details: [
          'TLS 1.3 for all client-server communications',
          'Perfect Forward Secrecy (PFS) implementation',
          'Strong cipher suites and protocols',
          'Certificate pinning for mobile applications',
          'End-to-end encryption for sensitive operations',
          'Regular SSL/TLS configuration reviews',
        ],
      },
      {
        subtitle: 'Data Classification',
        description: 'We classify and handle data according to sensitivity levels with appropriate security controls.',
        details: [
          'Automated data classification workflows',
          'Role-based access to classified data',
          'Data labeling and handling procedures',
          'Retention policies based on classification',
          'Secure disposal of sensitive information',
          'Regular data classification reviews',
        ],
      },
    ],
  },
  {
    id: 'access-controls',
    title: 'Access Controls & Authentication',
    icon: Key,
    content: [
      {
        subtitle: 'Multi-Factor Authentication',
        description: 'Strong authentication mechanisms protect user accounts and administrative access.',
        details: [
          'TOTP-based two-factor authentication',
          'Hardware security key support (FIDO2/WebAuthn)',
          'SMS backup authentication methods',
          'Single Sign-On (SSO) with SAML 2.0',
          'OAuth 2.0 and OpenID Connect support',
          'Adaptive authentication based on risk',
        ],
      },
      {
        subtitle: 'Identity & Access Management',
        description: 'Comprehensive IAM system ensures only authorized users can access resources.',
        details: [
          'Role-based access control (RBAC)',
          'Principle of least privilege enforcement',
          'Automated user provisioning and deprovisioning',
          'Regular access reviews and certifications',
          'Privileged access management (PAM)',
          'Just-in-time access for administrative tasks',
        ],
      },
      {
        subtitle: 'Session Management',
        description: 'Secure session handling prevents unauthorized access and session hijacking.',
        details: [
          'Secure session token generation',
          'Session timeout and idle detection',
          'Concurrent session monitoring',
          'Secure logout and session invalidation',
          'Cross-site request forgery (CSRF) protection',
          'Session fixation attack prevention',
        ],
      },
    ],
  },
  {
    id: 'infrastructure-security',
    title: 'Infrastructure Security',
    icon: Server,
    content: [
      {
        subtitle: 'Cloud Security',
        description: 'Our cloud infrastructure follows industry best practices for security and compliance.',
        details: [
          'AWS/GCP security-first architecture',
          'Virtual private cloud (VPC) isolation',
          'Network segmentation and micro-segmentation',
          'Web Application Firewall (WAF) protection',
          'DDoS protection and mitigation',
          'Automated security group management',
        ],
      },
      {
        subtitle: 'Container Security',
        description: 'Containerized applications are secured throughout the development and deployment lifecycle.',
        details: [
          'Container image vulnerability scanning',
          'Runtime security monitoring',
          'Immutable infrastructure practices',
          'Secrets management for containers',
          'Network policies and service mesh',
          'Container orchestration security',
        ],
      },
      {
        subtitle: 'Network Security',
        description: 'Multiple layers of network security protect against various threat vectors.',
        details: [
          'Intrusion Detection and Prevention (IDS/IPS)',
          'Network traffic monitoring and analysis',
          'Zero-trust network architecture',
          'Secure API gateway implementation',
          'Rate limiting and traffic shaping',
          'DNS security and filtering',
        ],
      },
    ],
  },
  {
    id: 'monitoring-response',
    title: 'Monitoring & Incident Response',
    icon: Monitor,
    content: [
      {
        subtitle: 'Security Monitoring',
        description: '24/7 security monitoring detects and responds to potential threats in real-time.',
        details: [
          'Security Information and Event Management (SIEM)',
          'Behavioral analytics and anomaly detection',
          'Threat intelligence integration',
          'Log aggregation and correlation',
          'Real-time alerting and notifications',
          'Security dashboards and reporting',
        ],
      },
      {
        subtitle: 'Incident Response',
        description: 'Comprehensive incident response procedures ensure rapid containment and recovery.',
        details: [
          'Dedicated security incident response team',
          'Documented incident response procedures',
          'Regular incident response drills',
          'Communication plans for stakeholders',
          'Forensic analysis capabilities',
          'Post-incident review and improvement',
        ],
      },
      {
        subtitle: 'Vulnerability Management',
        description: 'Proactive vulnerability identification and remediation processes.',
        details: [
          'Regular vulnerability assessments',
          'Automated security scanning tools',
          'Penetration testing by third parties',
          'Bug bounty program management',
          'Patch management procedures',
          'Zero-day vulnerability response',
        ],
      },
    ],
  },
  {
    id: 'compliance-certifications',
    title: 'Compliance & Certifications',
    icon: ShieldCheck,
    content: [
      {
        subtitle: 'SOC 2 Type II',
        description: 'Independent audit of our security, availability, and confidentiality controls.',
        details: [
          'Annual SOC 2 Type II examinations',
          'Security, Availability, Confidentiality criteria',
          'Independent third-party auditor verification',
          'Continuous monitoring of control effectiveness',
          'SOC 2 reports available to enterprise customers',
          'Remediation of audit findings',
        ],
      },
      {
        subtitle: 'ISO 27001',
        description: 'International standard for information security management systems.',
        details: [
          'Certified Information Security Management System',
          'Risk-based approach to security controls',
          'Regular internal and external audits',
          'Continual improvement processes',
          'Information security policy framework',
          'Employee security awareness training',
        ],
      },
      {
        subtitle: 'Privacy Regulations',
        description: 'Compliance with global privacy regulations and data protection laws.',
        details: [
          'General Data Protection Regulation (GDPR)',
          'California Consumer Privacy Act (CCPA)',
          'Personal Information Protection Act (PIPA)',
          'Data Processing Agreements (DPAs) available',
          'Privacy impact assessments',
          'Data subject rights management',
        ],
      },
    ],
  },
  {
    id: 'business-continuity',
    title: 'Business Continuity & Disaster Recovery',
    icon: Database,
    content: [
      {
        subtitle: 'Data Backup',
        description: 'Comprehensive backup strategies ensure data availability and recovery.',
        details: [
          'Automated daily incremental backups',
          'Weekly full backup procedures',
          'Multi-region backup replication',
          'Encrypted backup storage',
          'Regular backup restoration testing',
          'Point-in-time recovery capabilities',
        ],
      },
      {
        subtitle: 'Disaster Recovery',
        description: 'Tested disaster recovery procedures minimize downtime in case of incidents.',
        details: [
          'Recovery Time Objective (RTO): 4 hours',
          'Recovery Point Objective (RPO): 15 minutes',
          'Multi-zone failover capabilities',
          'Disaster recovery runbook procedures',
          'Regular DR testing and validation',
          'Communication protocols during incidents',
        ],
      },
      {
        subtitle: 'High Availability',
        description: 'Redundant systems and architecture ensure service availability.',
        details: [
          '99.9% uptime service level agreement',
          'Load balancing across multiple zones',
          'Auto-scaling based on demand',
          'Database clustering and replication',
          'CDN for global content delivery',
          'Health checks and automated failover',
        ],
      },
    ],
  },
];

// Security certifications and badges
const securityCertifications = [
  {
    name: 'SOC 2 Type II',
    description: 'Security, Availability, Confidentiality',
    icon: ShieldCheck,
    color: 'from-blue-600 to-cyan-500',
    status: 'Current',
  },
  {
    name: 'ISO 27001',
    description: 'Information Security Management',
    icon: Shield,
    color: 'from-green-600 to-emerald-500',
    status: 'Current',
  },
  {
    name: 'GDPR Compliant',
    description: 'European Privacy Regulation',
    icon: Eye,
    color: 'from-purple-600 to-pink-500',
    status: 'Current',
  },
  {
    name: 'CCPA Compliant',
    description: 'California Privacy Act',
    icon: FileCheck,
    color: 'from-orange-600 to-red-500',
    status: 'Current',
  },
];

// Security team contact
const securityContact = {
  officer: 'Michael Rodriguez',
  title: 'Chief Security Officer',
  email: 'security@serptank.com',
  phone: '+1 (555) 123-4567',
};

// Recent security updates
const securityUpdates = [
  {
    date: 'January 10, 2025',
    title: 'Enhanced MFA Implementation',
    description: 'Deployed WebAuthn support and hardware security keys',
    type: 'enhancement',
  },
  {
    date: 'December 15, 2024',
    title: 'SOC 2 Audit Completion',
    description: 'Successfully completed annual SOC 2 Type II examination',
    type: 'certification',
  },
  {
    date: 'November 20, 2024',
    title: 'Zero-Trust Architecture',
    description: 'Implemented zero-trust network security model',
    type: 'enhancement',
  },
  {
    date: 'October 5, 2024',
    title: 'Penetration Testing',
    description: 'Completed quarterly third-party security assessment',
    type: 'assessment',
  },
];

export default function SecurityPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState('data-protection');
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
      
      // Update active section based on scroll position
      const sections = securitySections.map(section => {
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
          <SEOOrb className="scale-150" />
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
              <ShieldCheck className="mr-1 h-3 w-3" />
              Security & Compliance
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Enterprise-Grade</span>
            <span className="block text-gradient-electric mt-2">Security</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Your data security is our top priority. We implement industry-leading security measures
            and compliance standards to protect your business information.
          </motion.p>

          <motion.div 
            className="flex items-center justify-center gap-8 text-sm text-muted-foreground"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-green-500" />
              <span>SOC 2 Type II</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-blue-500" />
              <span>ISO 27001</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-purple-500" />
              <span>GDPR Compliant</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Security Certifications */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              <span className="text-gradient-neon">Certified</span> & Compliant
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              We maintain the highest security standards through rigorous certifications and compliance programs
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            {securityCertifications.map((cert, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group"
              >
                <Card className="text-center h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative">
                    <div className={`w-16 h-16 bg-gradient-to-br ${cert.color} rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300`}>
                      <cert.icon className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-xl">{cert.name}</CardTitle>
                    <CardDescription className="text-base">
                      {cert.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative">
                    <Badge variant="default" className="bg-green-500/10 text-green-400 border-green-500/20">
                      {cert.status}
                    </Badge>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Security Content with Sidebar Navigation */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-4 gap-12">
            {/* Sticky Sidebar Navigation */}
            <div className="lg:col-span-1">
              <div className="sticky top-32">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-6">
                  Security Areas
                </h3>
                <nav className="space-y-2">
                  {securitySections.map((section) => (
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
                            {section.content.length} areas
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </nav>

                {/* Security Contact Card */}
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
                        <ShieldAlert className="h-5 w-5 text-primary" />
                        <span>Security Team</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 text-sm">
                        <div>
                          <div className="font-medium">{securityContact.officer}</div>
                          <div className="text-muted-foreground">{securityContact.title}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Mail className="h-4 w-4 text-accent" />
                          <a href={`mailto:${securityContact.email}`} className="text-accent hover:underline">
                            {securityContact.email}
                          </a>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          For security issues, vulnerabilities, or compliance questions
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Recent Updates */}
                <motion.div 
                  className="mt-6"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                >
                  <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                    <CardHeader>
                      <CardTitle className="text-lg">Recent Updates</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {securityUpdates.slice(0, 2).map((update, index) => (
                          <div key={index} className="space-y-1">
                            <div className="font-medium text-sm">{update.title}</div>
                            <div className="text-xs text-muted-foreground">{update.date}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              <div className="space-y-16">
                {securitySections.map((section, sectionIndex) => (
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

                {/* Security Updates History */}
                <motion.div
                  initial={{ opacity: 0, y: 50 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                  className="mt-16"
                >
                  <div className="flex items-center space-x-4 mb-8">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <AlertCircle className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-3xl font-bold">Recent Security Updates</h2>
                      <p className="text-muted-foreground mt-2">Latest security enhancements and certifications</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {securityUpdates.map((update, index) => (
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
                                  variant={
                                    update.type === 'certification' ? 'default' : 
                                    update.type === 'enhancement' ? 'secondary' : 
                                    'outline'
                                  }
                                >
                                  {update.type === 'certification' ? 'Certification' : 
                                   update.type === 'enhancement' ? 'Enhancement' : 
                                   'Assessment'}
                                </Badge>
                                <span className="font-medium">{update.date}</span>
                              </div>
                            </div>
                            <div className="mt-3">
                              <h3 className="font-semibold text-lg">{update.title}</h3>
                              <p className="text-muted-foreground mt-1">{update.description}</p>
                            </div>
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
            Questions About <span className="text-gradient-electric">Security</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Our security team is here to address any questions or concerns about data protection
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => window.open(`mailto:${securityContact.email}`, '_blank')}
              >
                Contact Security Team
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
                Security Documentation
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
        </motion.div>
      </section>

      {/* Modern Footer */}
      <footer className="relative py-16 border-t border-border">
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
              <Link href="/terms" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="/security" className="text-sm text-foreground font-medium">
                Security
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}