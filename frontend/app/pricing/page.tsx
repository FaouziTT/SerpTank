'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image'; // <-- CHANGE: Imported Image
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  CreditCard,
  DollarSign,
  Gauge,
  Globe,
  Headphones,
  Lock,
  MessageSquare,
  Minus,
  Phone,
  Plus,
  Rocket,
  Shield,
  Sparkles,
  Star,
  Trophy,
  Users,
  Zap,
  TrendingUp,
  X,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Animated counter for savings
const AnimatedSavings = ({ amount }: { amount: number }) => {
  const [count, setCount] = useState(0);
  const [ref, inView] = useInView({ triggerOnce: true });

  useEffect(() => {
    if (inView) {
      const timer = setInterval(() => {
        setCount(prev => {
          if (prev < amount) {
            return Math.min(prev + Math.ceil(amount / 50), amount);
          }
          return amount;
        });
      }, 30);
      return () => clearInterval(timer);
    }
  }, [inView, amount]);

  return (
    <span ref={ref} className="tabular-nums">
      ${count}
    </span>
  );
};

// Pricing plans with enhanced data
const pricingPlans = [
  {
    name: 'Starter',
    description: 'Perfect for small businesses and startups',
    monthlyPrice: 99,
    yearlyPrice: 79,
    badge: null,
    features: [
      { name: 'Up to 5 websites', included: true },
      { name: '10,000 pages tracked', included: true },
      { name: '1,000 keywords', included: true },
      { name: 'Weekly crawls', included: true },
      { name: 'Basic SEO diagnostics', included: true },
      { name: 'Email support', included: true },
      { name: '3 team members', included: true },
      { name: 'API access', included: false },
      { name: 'Custom reporting', included: false },
      { name: 'White-label options', included: false },
    ],
    cta: 'Start Free Trial',
    highlighted: false,
  },
  {
    name: 'Professional',
    description: 'For growing businesses and agencies',
    monthlyPrice: 299,
    yearlyPrice: 249,
    badge: 'Most Popular',
    features: [
      { name: 'Up to 25 websites', included: true },
      { name: '100,000 pages tracked', included: true },
      { name: '10,000 keywords', included: true },
      { name: 'Daily crawls', included: true },
      { name: 'Advanced SEO diagnostics', included: true },
      { name: 'Priority email support', included: true },
      { name: '10 team members', included: true },
      { name: 'API access (1M calls/mo)', included: true },
      { name: 'Custom reporting', included: true },
      { name: 'White-label options', included: false },
    ],
    cta: 'Start Free Trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    description: 'For large organizations with custom needs',
    monthlyPrice: null,
    yearlyPrice: null,
    badge: null,
    features: [
      { name: 'Unlimited websites', included: true },
      { name: 'Unlimited pages tracked', included: true },
      { name: 'Unlimited keywords', included: true },
      { name: 'Real-time crawls', included: true },
      { name: 'Enterprise SEO suite', included: true },
      { name: '24/7 phone & email support', included: true },
      { name: 'Unlimited team members', included: true },
      { name: 'API access (unlimited)', included: true },
      { name: 'Custom reporting & dashboards', included: true },
      { name: 'White-label options', included: true },
    ],
    cta: 'Contact Sales',
    highlighted: false,
  },
];

// Feature comparison data
const featureComparison = [
  {
    category: 'Core Features',
    features: [
      { name: 'SEO Diagnostics', starter: 'Basic', professional: 'Advanced', enterprise: 'Enterprise' },
      { name: 'Keyword Tracking', starter: '1,000', professional: '10,000', enterprise: 'Unlimited' },
      { name: 'Competitor Analysis', starter: '3 competitors', professional: '10 competitors', enterprise: 'Unlimited' },
      { name: 'Site Crawl Frequency', starter: 'Weekly', professional: 'Daily', enterprise: 'Real-time' },
      { name: 'Historical Data', starter: '3 months', professional: '12 months', enterprise: 'Unlimited' },
    ],
  },
  {
    category: 'Advanced Features',
    features: [
      { name: 'AI Market Simulation', starter: false, professional: true, enterprise: true },
      { name: 'Profitability Tracking', starter: false, professional: true, enterprise: true },
      { name: 'SGE Optimization', starter: false, professional: true, enterprise: true },
      { name: 'Content Workflow', starter: 'Basic', professional: 'Advanced', enterprise: 'Custom' },
      { name: 'Knowledge Engine', starter: false, professional: true, enterprise: true },
    ],
  },
  {
    category: 'Team & Collaboration',
    features: [
      { name: 'Team Members', starter: '3', professional: '10', enterprise: 'Unlimited' },
      { name: 'User Roles & Permissions', starter: 'Basic', professional: 'Advanced', enterprise: 'Custom' },
      { name: 'Projects/Workspaces', starter: '5', professional: '25', enterprise: 'Unlimited' },
      { name: 'Shared Dashboards', starter: false, professional: true, enterprise: true },
      { name: 'White-label Options', starter: false, professional: false, enterprise: true },
    ],
  },
  {
    category: 'Data & Integrations',
    features: [
      { name: 'API Access', starter: false, professional: '1M calls/mo', enterprise: 'Unlimited' },
      { name: 'Data Export', starter: 'CSV', professional: 'CSV, JSON', enterprise: 'Any format' },
      { name: 'Integrations', starter: 'Basic', professional: 'Premium', enterprise: 'Custom' },
      { name: 'Webhooks', starter: false, professional: true, enterprise: true },
      { name: 'SSO/SAML', starter: false, professional: false, enterprise: true },
    ],
  },
  {
    category: 'Support & Services',
    features: [
      { name: 'Support Channels', starter: 'Email', professional: 'Email (Priority)', enterprise: '24/7 Phone & Email' },
      { name: 'Response Time', starter: '24-48 hours', professional: '4-8 hours', enterprise: '< 1 hour' },
      { name: 'Dedicated Account Manager', starter: false, professional: false, enterprise: true },
      { name: 'Onboarding', starter: 'Self-service', professional: 'Guided', enterprise: 'White-glove' },
      { name: 'Custom Training', starter: false, professional: false, enterprise: true },
    ],
  },
];

// FAQs
const faqs = [
  {
    question: 'Can I change my plan anytime?',
    answer: 'Yes! You can upgrade or downgrade your plan at any time. When upgrading, you\'ll be charged the prorated difference. When downgrading, you\'ll receive account credit.',
  },
  {
    question: 'What happens after my free trial?',
    answer: 'Your 14-day free trial includes full access to all Professional plan features. After the trial, you can choose any plan that fits your needs. No credit card required to start.',
  },
  {
    question: 'Do you offer discounts for nonprofits?',
    answer: 'Yes, we offer 50% off all plans for qualified nonprofit organizations. Contact our sales team with your 501(c)(3) documentation to apply.',
  },
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards, ACH transfers, and wire transfers for annual plans. Enterprise customers can also pay by invoice with NET 30 terms.',
  },
  {
    question: 'Is there a setup fee?',
    answer: 'No setup fees for Starter and Professional plans. Enterprise plans may include one-time implementation fees depending on customization requirements.',
  },
  {
    question: 'Can I get a demo before signing up?',
    answer: 'Absolutely! We offer personalized demos for all potential customers. Book a demo to see how SerpTank can transform your SEO strategy.',
  },
];

// Pricing card component with animations
const PricingCard = ({ plan, index, billingPeriod, router }: any) => {
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 });
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      whileHover={{ y: -10 }}
      className={`relative group ${plan.highlighted ? 'z-10' : ''}`}
      style={{ paddingTop: plan.badge ? '1rem' : '0' }}
    >
      <Card className={`relative h-full bg-card/95 backdrop-blur-sm transition-all duration-300 ${
        plan.highlighted 
          ? 'border-2 border-primary shadow-2xl shadow-primary/10 scale-105' 
          : 'border border-border/50 hover:border-primary/50 shadow-lg hover:shadow-xl'
      }`}>
        {/* Gradient background on hover */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        
        {plan.badge && (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
            <Badge className={`px-4 py-1 text-xs font-semibold ${
              plan.highlighted 
                ? 'bg-primary text-primary-foreground border-0 shadow-md' 
                : 'bg-card border-primary'
            }`}>
              {plan.badge === 'Most Popular' && <Star className="mr-1 h-3 w-3" />}
              {plan.badge}
            </Badge>
          </div>
        )}
        
        <CardHeader className="text-center pb-8 pt-8 relative">
          <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 mx-auto ${
            plan.name === 'Starter' ? 'bg-blue-100 dark:bg-blue-900/30' :
            plan.name === 'Professional' ? 'bg-purple-100 dark:bg-purple-900/30' :
            'bg-orange-100 dark:bg-orange-900/30'
          } group-hover:scale-110 transition-transform duration-300`}>
            {plan.name === 'Starter' && <Rocket className="h-8 w-8 text-blue-600 dark:text-blue-400" />}
            {plan.name === 'Professional' && <TrendingUp className="h-8 w-8 text-purple-600 dark:text-purple-400" />}
            {plan.name === 'Enterprise' && <Building2 className="h-8 w-8 text-orange-600 dark:text-orange-400" />}
          </div>
          
          <CardTitle className="text-2xl mb-2">{plan.name}</CardTitle>
          <CardDescription className="text-base">{plan.description}</CardDescription>
          
          <div className="mt-6">
            {plan.monthlyPrice ? (
              <div className="space-y-2">
                <div className="flex items-baseline justify-center">
                  <span className="text-6xl font-extrabold tracking-tight">
                    ${billingPeriod === 'monthly' ? plan.monthlyPrice : plan.yearlyPrice}
                  </span>
                  <span className="text-muted-foreground ml-2">/month</span>
                </div>
                {billingPeriod === 'yearly' && (
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      Billed ${plan.yearlyPrice * 12} yearly
                    </p>
                    <p className="text-sm font-medium text-green-600 dark:text-green-400">
                      Save <AnimatedSavings amount={(plan.monthlyPrice - plan.yearlyPrice) * 12} /> per year
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-4xl font-bold text-primary">Custom Pricing</div>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4 relative px-8">
          <ul className="space-y-4">
            {plan.features.map((feature: any, idx: number) => (
              <motion.li 
                key={idx} 
                className="flex items-start"
                initial={{ opacity: 0, x: -20 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: index * 0.1 + idx * 0.05 }}
              >
                {feature.included ? (
                  <CheckCircle2 className="h-5 w-5 text-accent mr-3 flex-shrink-0 mt-0.5" />
                ) : (
                  <Minus className="h-5 w-5 text-muted-foreground/20 mr-3 flex-shrink-0 mt-0.5" />
                )}
                <span className={`text-sm ${
                  feature.included ? '' : 'text-muted-foreground/40'
                }`}>
                  {feature.name}
                </span>
              </motion.li>
            ))}
          </ul>
        </CardContent>

        <CardFooter className="relative p-6 pt-2">
          <SimpleMagneticWrapper className="w-full">
            {plan.highlighted ? (
              <CTAButton
                className="w-full"
                size="lg"
                onClick={() => 
                  plan.name === 'Enterprise'
                    ? router.push('/contact-sales')
                    : router.push('/register')
                }
              >
                {plan.cta}
                <ArrowRight className="ml-2 h-4 w-4" />
              </CTAButton>
            ) : (
              <MagneticButton
                variant={plan.name === 'Enterprise' ? 'primary' : 'secondary'}
                size="lg"
                className="w-full"
                onClick={() => 
                  plan.name === 'Enterprise'
                    ? router.push('/contact-sales')
                    : router.push('/register')
                }
                magneticStrength={0}
              >
                <div className="flex items-center justify-center gap-2">
                  <span>{plan.cta}</span>
                  <ArrowRight className="h-4 w-4" />
                </div>
              </MagneticButton>
            )}
          </SimpleMagneticWrapper>
        </CardFooter>
      </Card>
    </motion.div>
  );
};

export default function PricingPage() {
  const router = useRouter();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('yearly');
  const [expandedFAQ, setExpandedFAQ] = useState<number | null>(null);
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleFAQ = (index: number) => {
    setExpandedFAQ(expandedFAQ === index ? null : index);
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
                  {/* CHANGE: Replaced <img> with <Image> */}
                  <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={40} height={40} className="w-full h-full object-contain" />
                </div>
                <span className="text-2xl font-bold tracking-tight">SerpTank</span>
              </Link>
              <div className="hidden lg:flex items-center space-x-8">
                <Link
                  href="/"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Home
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/features"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Features
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/pricing"
                  className="text-sm font-medium text-foreground relative group"
                >
                  Pricing
                  <span className="absolute -bottom-1 left-0 w-full h-0.5 bg-primary" />
                </Link>
                <Link
                  href="/case-studies"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Case Studies
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/about"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  About
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
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
        <div className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10" />
        
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
              <CreditCard className="mr-1 h-3 w-3" />
              Transparent Pricing
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Choose the Perfect Plan</span>
            <span className="block text-gradient-neon mt-2">for Your Business</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Start with a 14-day free trial. No credit card required.
            Scale up as your business grows with flexible, transparent pricing.
          </motion.p>

          {/* Billing Toggle with Animation */}
          <motion.div 
            className="flex items-center justify-center space-x-4"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <span className={`text-sm font-medium transition-colors ${billingPeriod === 'monthly' ? 'text-foreground' : 'text-muted-foreground'}`}>
              Monthly
            </span>
            <Switch
              checked={billingPeriod === 'yearly'}
              onCheckedChange={(checked) => setBillingPeriod(checked ? 'yearly' : 'monthly')}
              className="data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-primary data-[state=checked]:to-accent"
            />
            <span className={`text-sm font-medium transition-colors ${billingPeriod === 'yearly' ? 'text-foreground' : 'text-muted-foreground'}`}>
              Yearly
            </span>
            <Badge className="ml-2 bg-gradient-to-r from-green-600 to-emerald-500 text-white border-0">
              <Sparkles className="mr-1 h-3 w-3" />
              Save 20%
            </Badge>
          </motion.div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Pricing Cards */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <div className="grid md:grid-cols-3 gap-8 md:gap-6 lg:gap-8 mt-8">
            {pricingPlans.map((plan, index) => (
              <PricingCard 
                key={index}
                plan={plan}
                index={index}
                billingPeriod={billingPeriod}
                router={router}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Enterprise CTA with Enhanced Design */}
      <section className="relative section-padding bg-gray-50/40 dark:bg-gray-950/40">
        <div className="container-width px-6 mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <Card className="relative overflow-hidden bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white border-0">
              {/* Animated gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-accent/10 to-destructive/10 animate-gradient-shift" />
              
              <CardContent className="relative p-8 md:p-12 lg:p-16">
                <div className="grid md:grid-cols-2 gap-12 items-center">
                  <div>
                    <Badge className="mb-6 bg-white/10 text-white backdrop-blur-sm border-white/20">
                      <Building2 className="mr-1 h-3 w-3" />
                      Enterprise Solutions
                    </Badge>
                    <h3 className="text-4xl sm:text-5xl font-bold mb-6">
                      Need a <span className="text-gradient-electric">Custom Solution</span>?
                    </h3>
                    <p className="text-lg sm:text-xl opacity-90 mb-8 leading-relaxed">
                      Get a tailored plan with custom features, dedicated support,
                      and enterprise-grade security for your organization.
                    </p>
                    <ul className="space-y-4 mb-8">
                      <motion.li 
                        className="flex items-center"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                      >
                        <CheckCircle2 className="h-6 w-6 mr-3 text-accent flex-shrink-0" />
                        <span>Custom pricing based on your needs</span>
                      </motion.li>
                      <motion.li 
                        className="flex items-center"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                      >
                        <CheckCircle2 className="h-6 w-6 mr-3 text-accent flex-shrink-0" />
                        <span>Dedicated customer success manager</span>
                      </motion.li>
                      <motion.li 
                        className="flex items-center"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3 }}
                      >
                        <CheckCircle2 className="h-6 w-6 mr-3 text-accent flex-shrink-0" />
                        <span>SLA guarantees and priority support</span>
                      </motion.li>
                    </ul>
                  </div>
                  <div className="flex flex-col items-center text-center">
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      whileInView={{ scale: 1, opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6 }}
                      className="relative"
                    >
                      <Trophy className="h-24 w-24 mb-6 text-yellow-400 relative z-10" />
                      <div className="absolute inset-0 bg-yellow-400/20 blur-3xl" />
                    </motion.div>
                    <SimpleMagneticWrapper>
                      <CTAButton
                        size="xl"
                        onClick={() => router.push('/contact-sales')}
                        className="mb-4"
                      >
                        Contact Sales Team
                        <Phone className="ml-2 h-5 w-5" />
                      </CTAButton>
                    </SimpleMagneticWrapper>
                    <p className="text-sm opacity-75">
                      Response within 24 hours
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Feature Comparison with Modern Table */}
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
              <span className="text-gradient">Detailed Feature</span> Comparison
            </h2>
            <p className="text-xl text-muted-foreground">
              See exactly what&apos;s included in each plan
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <Card className="overflow-hidden bg-card/80 backdrop-blur-sm border-border/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border/50 bg-card/50">
                      <th className="text-left p-6 font-semibold min-w-[200px]">Features</th>
                      <th className="text-center p-6 font-semibold min-w-[150px]">
                        <div className="text-center">
                          <div className="font-semibold flex items-center justify-center mb-1">
                            <Rocket className="mr-2 h-5 w-5 text-blue-500" />
                            Starter
                          </div>
                          <div className="text-sm text-muted-foreground">
                            ${billingPeriod === 'monthly' ? '99' : '79'}/mo
                          </div>
                        </div>
                      </th>
                      <th className="text-center p-6 font-semibold min-w-[150px]">
                        <div className="text-center">
                          <div className="font-semibold flex items-center justify-center mb-1">
                            <TrendingUp className="mr-2 h-5 w-5 text-purple-500" />
                            Professional
                            <Star className="ml-1 h-4 w-4 text-yellow-500" />
                          </div>
                          <div className="text-sm text-muted-foreground">
                            ${billingPeriod === 'monthly' ? '299' : '249'}/mo
                          </div>
                        </div>
                      </th>
                      <th className="text-center p-6 font-semibold min-w-[150px]">
                        <div className="text-center">
                          <div className="font-semibold flex items-center justify-center mb-1">
                            <Building2 className="mr-2 h-5 w-5 text-orange-500" />
                            Enterprise
                          </div>
                          <div className="text-sm text-muted-foreground">Custom</div>
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {featureComparison.map((category, catIdx) => (
                      <React.Fragment key={catIdx}>
                        <tr className="border-b border-border/30 bg-card/30">
                          <td colSpan={4} className="p-4 font-semibold text-sm uppercase tracking-wider text-primary">
                            {category.category}
                          </td>
                        </tr>
                        {category.features.map((feature, featIdx) => (
                          <motion.tr 
                            key={featIdx} 
                            className="border-b border-border/20 hover:bg-card/30 transition-colors"
                            initial={{ opacity: 0 }}
                            whileInView={{ opacity: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: catIdx * 0.1 + featIdx * 0.05 }}
                          >
                            <td className="p-6">{feature.name}</td>
                            <td className="text-center p-6">
                              {typeof feature.starter === 'boolean' ? (
                                feature.starter ? (
                                  <CheckCircle2 className="h-5 w-5 text-accent mx-auto" />
                                ) : (
                                  <Minus className="h-4 w-4 text-muted-foreground/20 mx-auto" />
                                )
                              ) : (
                                <span className="text-sm font-medium">{feature.starter}</span>
                              )}
                            </td>
                            <td className="text-center p-6">
                              {typeof feature.professional === 'boolean' ? (
                                feature.professional ? (
                                  <CheckCircle2 className="h-5 w-5 text-accent mx-auto" />
                                ) : (
                                  <Minus className="h-4 w-4 text-muted-foreground/20 mx-auto" />
                                )
                              ) : (
                                <span className="text-sm font-medium">{feature.professional}</span>
                              )}
                            </td>
                            <td className="text-center p-6">
                              {typeof feature.enterprise === 'boolean' ? (
                                feature.enterprise ? (
                                  <CheckCircle2 className="h-5 w-5 text-accent mx-auto" />
                                ) : (
                                  <Minus className="h-4 w-4 text-muted-foreground/20 mx-auto" />
                                )
                              ) : (
                                <span className="text-sm font-medium text-gradient">{feature.enterprise}</span>
                              )}
                            </td>
                          </motion.tr>
                        ))}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* FAQs with Enhanced Animations */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Frequently Asked <span className="text-gradient-electric">Questions</span>
            </h2>
            <p className="text-xl text-muted-foreground">
              Everything you need to know about our pricing
            </p>
          </motion.div>

          <div className="max-w-3xl mx-auto space-y-4">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="overflow-hidden bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                  <CardHeader
                    className="cursor-pointer"
                    onClick={() => toggleFAQ(index)}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-lg pr-8">{faq.question}</h3>
                      <motion.div
                        animate={{ rotate: expandedFAQ === index ? 180 : 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                      </motion.div>
                    </div>
                  </CardHeader>
                  <motion.div
                    initial={false}
                    animate={{ height: expandedFAQ === index ? 'auto' : 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <CardContent className="pt-0">
                      <p className="text-muted-foreground leading-relaxed">{faq.answer}</p>
                    </CardContent>
                  </motion.div>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* CTA Section with Gradient Background */}
      <section className="relative section-padding overflow-hidden">
        {/* Gradient background */}
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
            Start Your <span className="text-gradient-neon">14-Day Free Trial</span>
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            No credit card required. Full access to all Professional features.
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center mb-12">
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
                onClick={() => router.push('/contact-sales')}
                className="text-xl"
                magneticStrength={0}
              >
                <MessageSquare className="mr-2 h-5 w-5" />
                Talk to Sales
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
          <div className="flex items-center justify-center flex-wrap gap-8 text-sm text-muted-foreground">
            <div className="flex items-center">
              <Lock className="h-4 w-4 mr-2 text-accent" />
              SSL Encrypted
            </div>
            <div className="flex items-center">
              <Shield className="h-4 w-4 mr-2 text-accent" />
              SOC 2 Compliant
            </div>
            <div className="flex items-center">
              <Clock className="h-4 w-4 mr-2 text-accent" />
              Cancel Anytime
            </div>
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
                  {/* CHANGE: Replaced <img> with <Image> */}
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