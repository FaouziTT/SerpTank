'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image'; // <-- CHANGE: Imported Image
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { ThemeToggle } from '@/components/theme-toggle';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import {
  ArrowRight,
  Activity,
  Brain,
  DollarSign,
  FileText,
  Sparkles,
  BookOpen,
  Shield,
  Users,
  Zap,
  Globe,
  ChevronRight,
  Play,
  TrendingUp,
  Code,
  BarChart3,
  Network,
  Layers,
  Timer,
  CheckCircle2,
  Star,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Company logos data
const companyLogos = [
  { name: 'Stripe', logo: '🔷' },
  { name: 'Spotify', logo: '🎵' },
  { name: 'Airbnb', logo: '🏠' },
  { name: 'Netflix', logo: '🎬' },
  { name: 'Tesla', logo: '⚡' },
  { name: 'GitHub', logo: '🐙' },
  { name: 'Figma', logo: '🎨' },
  { name: 'Notion', logo: '📝' },
];

// Animated metrics counter with compact formatting for large numbers
const AnimatedCounter = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [count, setCount] = useState(0);
  const [ref, inView] = useInView({ triggerOnce: true });

  useEffect(() => {
    if (inView) {
      const timer = setInterval(() => {
        setCount(prev => {
          if (prev < value) {
            return Math.min(prev + Math.ceil(value / 50), value);
          }
          return value;
        });
      }, 30);
      return () => clearInterval(timer);
    }
  }, [inView, value]);

  // Format large numbers more compactly
  const formatNumber = (num: number) => {
    if (num >= 10000000) {
      return (num / 1000000).toFixed(0) + 'M';
    } else if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 100000) {
      return (num / 1000).toFixed(0) + 'k';
    } else if (num >= 10000) {
      return num.toLocaleString('en-US');
    }
    return num.toLocaleString('en-US');
  };

  return (
    <span ref={ref} className="tabular-nums inline-block font-bold">
      {formatNumber(count)}{suffix}
    </span>
  );
};

// Feature card with floating animation
const FeatureCard = ({ feature, index }: { feature: any; index: number }) => {
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 });
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      whileHover={{ y: -10 }}
      className="group"
    >
      <Card className="relative h-full p-8 lg:p-10 bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
        {/* Subtle gradient background on hover */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        
        {/* Icon with subtle glow effect */}
        <div className="relative mb-8">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center group-hover:from-primary/20 group-hover:to-accent/20 transition-all duration-300">
            <feature.icon className="h-10 w-10 text-primary group-hover:scale-110 transition-transform duration-300" />
          </div>
        </div>
        
        {/* Content */}
        <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
        <p className="text-muted-foreground mb-8 leading-relaxed">{feature.description}</p>
        
        {/* Benefits with stagger animation */}
        <ul className="space-y-2">
          {feature.benefits.map((benefit: string, idx: number) => (
            <motion.li
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: index * 0.1 + idx * 0.05 }}
              className="flex items-center text-sm"
            >
              <CheckCircle2 className="mr-2 h-4 w-4 text-accent flex-shrink-0" />
              <span>{benefit}</span>
            </motion.li>
          ))}
        </ul>
      </Card>
    </motion.div>
  );
};

export default function ModernLandingPage() {
  const router = useRouter();
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

  const metrics = [
    { label: 'Active Users', value: 50000, suffix: '+', icon: Users },
    { label: 'Websites Analyzed', value: 2000000, suffix: '+', icon: Globe },
    { label: 'Keywords Tracked', value: 10000000, suffix: '+', icon: BarChart3 },
    { label: 'Avg ROI', value: 312, suffix: '%', icon: TrendingUp },
  ];

  const features = [
    {
      icon: Activity,
      title: 'AI-Powered Diagnostics',
      description: 'Real-time site analysis with machine learning insights',
      benefits: ['200+ automated checks', 'Predictive issue detection', 'Smart prioritization'],
    },
    {
      icon: Brain,
      title: 'Market Intelligence',
      description: 'Stay ahead with AI-driven competitive analysis',
      benefits: ['Competitor tracking', 'Trend prediction', 'Opportunity alerts'],
    },
    {
      icon: DollarSign,
      title: 'Revenue Attribution',
      description: 'Connect SEO directly to business outcomes',
      benefits: ['Revenue tracking', 'ROI calculation', 'Profit forecasting'],
    },
    {
      icon: FileText,
      title: 'Content Automation',
      description: 'AI-assisted content optimization at scale',
      benefits: ['Auto-optimization', 'Workflow automation', 'Quality scoring'],
    },
    {
      icon: Sparkles,
      title: 'SGE Optimization',
      description: 'Future-proof your content for AI search',
      benefits: ['SGE compatibility', 'AI-first content', 'Featured snippets'],
    },
    {
      icon: BookOpen,
      title: 'Knowledge Graph',
      description: 'Build topical authority with intelligent mapping',
      benefits: ['Entity recognition', 'Topic clusters', 'Authority scoring'],
    },
  ];

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
            <div className="flex items-center space-x-4">
              <ThemeToggle />
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

      {/* Hero Section with 3D Elements */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
        {/* Background gradient mesh */}
        <div className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10" />
        
        {/* Enhanced floating 3D orb */}
        <motion.div
          className="absolute right-[-200px] top-1/2 -translate-y-1/2 w-[800px] h-[800px] lg:w-[1000px] lg:h-[1000px]"
          style={{ y: heroY, scale: orbScale }}
        >
          <SEOOrb className="scale-150" />
        </motion.div>

        {/* Hero content with better spacing */}
        <div className="container-width px-6 mx-auto relative z-10 py-12">
          <div className="max-w-4xl">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <Badge variant="secondary" className="mb-6 animate-slide-up-fade">
                <Sparkles className="mr-1 h-3 w-3" />
                AI-Powered SEO Intelligence Platform
              </Badge>
            </motion.div>
            
            <motion.h1
              className="text-6xl sm:text-7xl md:text-8xl lg:text-9xl font-bold tracking-tighter mb-8 leading-[0.9]"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
            >
              <span className="block">SEO that</span>
              <span className="block text-gradient-electric">actually drives</span>
              <span className="block">revenue.</span>
            </motion.h1>
            
            <motion.p
              className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-2xl leading-relaxed"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              The only platform that combines real-time diagnostics, AI insights, 
              and profit tracking to transform your organic growth.
            </motion.p>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
            >
              <div className="flex flex-col sm:flex-row gap-6 md:gap-8 mb-20 items-start">
                <SimpleMagneticWrapper>
                  <CTAButton
                    size="xl"
                    onClick={() => router.push('/register')}
                  >
                    Start 14-Day Free Trial
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </CTAButton>
                </SimpleMagneticWrapper>
                <SimpleMagneticWrapper>
                  <MagneticButton
                    variant="glass"
                    size="xl"
                    onClick={() => router.push('/demo')}
                    magneticStrength={0}
                  >
                    <Play className="mr-2 h-5 w-5" />
                    Watch Live Demo
                  </MagneticButton>
                </SimpleMagneticWrapper>
              </div>
            </motion.div>

            {/* Live metrics */}
            <motion.div
              className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              {metrics.map((metric, index) => (
                <div key={index} className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-accent/5 rounded-2xl blur-lg group-hover:from-primary/10 group-hover:to-accent/10 transition-all" />
                  <div className="relative bg-card/80 backdrop-blur-sm border border-border/30 rounded-2xl p-4 sm:p-6 hover:border-border/50 transition-colors h-full min-h-[140px] flex flex-col">
                    <metric.icon className="h-5 w-5 sm:h-6 sm:w-6 text-primary/80 mb-3 flex-shrink-0" />
                    <div className="flex-grow flex flex-col justify-between">
                      <div className="metric-number text-xl sm:text-2xl lg:text-3xl mb-2 break-words">
                        <AnimatedCounter value={metric.value} suffix={metric.suffix} />
                      </div>
                      <div className="text-xs sm:text-sm text-muted-foreground">{metric.label}</div>
                    </div>
                  </div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>

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
      </section>

      {/* Features Grid with Bento Layout */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto">
          <div className="text-center mb-20">
            <motion.h2
              className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              Everything you need to
              <span className="block text-gradient-neon mt-2">dominate search</span>
            </motion.h2>
            <motion.p
              className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              Six core pillars powered by artificial intelligence and decades of SEO expertise
            </motion.p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <FeatureCard key={index} feature={feature} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Demo Section */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-4xl sm:text-5xl font-bold mb-6">
                See your SEO
                <span className="block text-gradient mt-2">in real-time</span>
              </h2>
              <p className="text-lg sm:text-xl text-muted-foreground mb-10 leading-relaxed">
                {/* CHANGE: Escaped apostrophes */}
                Our dashboard gives you instant visibility into what&apos;s working, 
                what&apos;s not, and exactly what to do next.
              </p>
              
              <div className="space-y-4">
                {[
                  'Live performance monitoring across 200+ metrics',
                  'AI-powered recommendations updated hourly',
                  'Direct revenue attribution for every keyword',
                  'Competitor tracking with opportunity alerts',
                ].map((item, index) => (
                  <motion.div
                    key={index}
                    className="flex items-start"
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <CheckCircle2 className="h-6 w-6 text-accent mt-1 mr-3 flex-shrink-0" />
                    <span className="text-lg">{item}</span>
                  </motion.div>
                ))}
              </div>

              <div className="flex gap-4 mt-8">
                <SimpleMagneticWrapper>
                  <CTAButton
                    size="lg"
                    onClick={() => router.push('/demo')}
                  >
                    Try Interactive Demo
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </CTAButton>
                </SimpleMagneticWrapper>
              </div>
            </motion.div>

            <motion.div
              className="relative"
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              {/* Enhanced Dashboard preview */}
              <div className="relative rounded-2xl overflow-hidden shadow-2xl group cursor-pointer" onClick={() => router.push('/demo')}>
                <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 via-accent/20 to-primary/20 animate-glow-pulse" />
                <div className="relative bg-card border border-border overflow-hidden">
                  {/* Mock dashboard UI */}
                  <div className="bg-card/80 backdrop-blur-sm p-4 border-b border-border">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="h-8 w-32 bg-muted/50 rounded" />
                        <div className="flex gap-2">
                          <div className="h-8 w-20 bg-muted/30 rounded" />
                          <div className="h-8 w-20 bg-muted/30 rounded" />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <div className="h-8 w-8 bg-muted/30 rounded" />
                        <div className="h-8 w-8 bg-muted/30 rounded" />
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-6">
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg p-4">
                        <div className="h-3 w-16 bg-primary/30 rounded mb-2" />
                        <div className="text-2xl font-bold text-primary">+347%</div>
                        <div className="h-2 w-12 bg-muted/30 rounded mt-2" />
                      </div>
                      <div className="bg-gradient-to-br from-accent/10 to-accent/5 rounded-lg p-4">
                        <div className="h-3 w-16 bg-accent/30 rounded mb-2" />
                        <div className="text-2xl font-bold text-accent">89/100</div>
                        <div className="h-2 w-12 bg-muted/30 rounded mt-2" />
                      </div>
                      <div className="bg-gradient-to-br from-destructive/10 to-destructive/5 rounded-lg p-4">
                        <div className="h-3 w-16 bg-destructive/30 rounded mb-2" />
                        <div className="text-2xl font-bold text-destructive">$24.5k</div>
                        <div className="h-2 w-12 bg-muted/30 rounded mt-2" />
                      </div>
                    </div>
                    
                    <div className="bg-muted/10 rounded-lg p-4 mb-4">
                      <div className="h-32 flex items-end justify-between gap-2">
                        {[65, 80, 45, 90, 70, 85, 95].map((height, i) => (
                          <div key={i} className="flex-1 bg-gradient-to-t from-primary to-accent rounded-t" style={{ height: `${height}%` }} />
                        ))}
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-center gap-2 text-muted-foreground group-hover:text-primary transition-colors">
                      <Play className="h-5 w-5" />
                      <span className="text-sm font-medium">Click for interactive demo</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Trust Section */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-4">
              Trusted by <span className="text-gradient-electric">10,000+</span> companies
            </h2>
            <p className="text-lg text-muted-foreground mb-16 max-w-2xl mx-auto">
              From startups to Fortune 500, leading companies trust SerpTank to drive their organic growth
            </p>
          </motion.div>

          {/* Logo cloud with real company representation */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-8 items-center justify-items-center">
            {companyLogos.map((company, index) => (
              <motion.div
                key={index}
                className="relative group w-full"
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
              >
                <div className="h-20 w-full bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl flex flex-col items-center justify-center group-hover:bg-card/80 group-hover:border-primary/50 transition-all duration-300 cursor-pointer">
                  <div className="text-3xl mb-1 group-hover:scale-110 transition-transform">
                    {company.logo}
                  </div>
                  <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                    {company.name}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
          
          {/* Trust badges */}
          <motion.div
            className="mt-16 flex flex-wrap justify-center gap-8"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
          >
            <div className="flex items-center gap-2 text-muted-foreground">
              <Shield className="h-5 w-5 text-primary" />
              <span className="text-sm">SOC2 Compliant</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <CheckCircle2 className="h-5 w-5 text-accent" />
              <span className="text-sm">99.9% Uptime SLA</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Zap className="h-5 w-5 text-destructive" />
              <span className="text-sm">Real-time Updates</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative section-padding overflow-hidden">
        {/* Softer gradient background */}
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
          {/* Live users indicator */}
          <motion.div
            className="inline-flex items-center gap-2 mb-8"
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <div className="relative">
              <div className="absolute inset-0 bg-green-500 rounded-full animate-ping" />
              <div className="relative w-3 h-3 bg-green-500 rounded-full" />
            </div>
            <span className="text-sm text-muted-foreground">
              <AnimatedCounter value={2847} /> marketers online now
            </span>
          </motion.div>
          
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
            Ready to <span className="text-gradient-neon">10x</span> your organic growth?
          </h2>
          <p className="text-lg sm:text-xl text-muted-foreground mb-12 max-w-2xl mx-auto leading-relaxed">
            Join thousands of companies using SerpTank to transform their SEO
          </p>
          
          <div className="flex flex-col sm:flex-row gap-6 md:gap-8 justify-center mb-8">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => router.push('/register')}
              >
                Start Free 14-Day Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="secondary"
                size="xl"
                onClick={() => router.push('/contact')}
                magneticStrength={0}
              >
                Talk to Sales
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
          
          <p className="text-sm text-muted-foreground mb-8">
            No credit card required • Full access • Cancel anytime
          </p>
          
          {/* Social proof */}
          <motion.div
            className="flex flex-wrap items-center justify-center gap-8"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
          >
            <div className="flex items-center gap-2">
              <div className="flex -space-x-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-xs font-bold border-2 border-background">
                    {String.fromCharCode(65 + i)}
                  </div>
                ))}
              </div>
              <span className="text-sm text-muted-foreground">5,000+ happy customers</span>
            </div>
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-yellow-500 text-yellow-500" />
              ))}
              <span className="text-sm text-muted-foreground ml-2">4.9/5 rating</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Modern Footer */}
      <footer className="relative py-16 border-t border-border">
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