'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image'; // <-- CHANGE #1: Imported Next.js Image component
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import {
  ArrowRight,
  Award,
  BarChart3,
  Brain,
  Building2,
  Calendar,
  CheckCircle,
  CheckCircle2,
  ChevronRight,
  Globe,
  Heart,
  Lightbulb,
  MapPin,
  Rocket,
  Shield,
  Sparkles,
  Star,
  Target,
  Trophy,
  Users,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Animated counter component
const AnimatedCounter = ({ value }: { value: string }) => {
  const [count, setCount] = useState(0);
  const [ref, inView] = useInView({ triggerOnce: true });
  const numericValue = parseInt(value.replace(/[^0-9]/g, ''));
  
  useEffect(() => {
    if (inView && numericValue) {
      const timer = setInterval(() => {
        setCount(prev => {
          if (prev < numericValue) {
            return Math.min(prev + Math.ceil(numericValue / 50), numericValue);
          }
          return numericValue;
        });
      }, 30);
      return () => clearInterval(timer);
    }
  }, [inView, numericValue]);

  if (!numericValue) return <span>{value}</span>;
  
  const suffix = value.replace(/[0-9]/g, '');
  return (
    <span ref={ref} className="tabular-nums">
      {count}{suffix}
    </span>
  );
};

// Company stats
const companyStats = [
  { label: 'Founded', value: '2019' },
  { label: 'Team Members', value: '120+' },
  { label: 'Countries', value: '45+' },
  { label: 'Customers', value: '5,000+' },
];

// Core values
const coreValues = [
  {
    icon: Lightbulb,
    title: 'Innovation First',
    description: 'We push the boundaries of SEO technology with AI and machine learning to deliver cutting-edge solutions.',
    gradient: 'from-blue-600 to-cyan-500',
  },
  {
    icon: Users,
    title: 'Customer Success',
    description: 'Your success is our success. We\'re committed to helping you achieve measurable business results.',
    gradient: 'from-purple-600 to-pink-500',
  },
  {
    icon: Shield,
    title: 'Trust & Security',
    description: 'We take data security seriously with enterprise-grade protection and compliance certifications.',
    gradient: 'from-green-600 to-emerald-500',
  },
  {
    icon: Heart,
    title: 'Transparency',
    description: 'Clear pricing, honest communication, and no hidden surprises in our platform or business.',
    gradient: 'from-orange-600 to-red-500',
  },
];

// Leadership team
const leadershipTeam = [
  {
    name: 'Sarah Chen',
    role: 'CEO & Co-founder',
    bio: 'Former Google Search Quality team lead with 15+ years in search and AI.',
    image: '👩‍💼',
    gradient: 'from-blue-600 to-cyan-500',
  },
  {
    name: 'Michael Rodriguez',
    role: 'CTO & Co-founder',
    bio: 'Ex-Amazon principal engineer, specialist in large-scale data processing.',
    image: '👨‍💻',
    gradient: 'from-purple-600 to-pink-500',
  },
  {
    name: 'Jennifer Park',
    role: 'VP of Product',
    bio: 'Product visionary with experience at Microsoft and HubSpot.',
    image: '👩‍🔬',
    gradient: 'from-green-600 to-emerald-500',
  },
  {
    name: 'David Thompson',
    role: 'VP of Customer Success',
    bio: 'Built customer success teams at Salesforce and Adobe.',
    image: '👨‍💼',
    gradient: 'from-orange-600 to-amber-500',
  },
];

// Company milestones
const milestones = [
  {
    year: '2019',
    title: 'Company Founded',
    description: 'Started with a vision to democratize enterprise SEO tools',
    icon: Rocket,
    gradient: 'from-blue-600 to-cyan-500',
  },
  {
    year: '2020',
    title: 'Series A Funding',
    description: 'Raised $15M to accelerate product development',
    icon: Trophy,
    gradient: 'from-purple-600 to-pink-500',
  },
  {
    year: '2021',
    title: 'AI Integration',
    description: 'Launched industry-first AI-powered SEO predictions',
    icon: Brain,
    gradient: 'from-green-600 to-emerald-500',
  },
  {
    year: '2022',
    title: 'Global Expansion',
    description: 'Opened offices in London, Singapore, and São Paulo',
    icon: Globe,
    gradient: 'from-orange-600 to-red-500',
  },
  {
    year: '2023',
    title: 'Enterprise Launch',
    description: 'Released enterprise features for Fortune 500 companies',
    icon: Building2,
    gradient: 'from-indigo-600 to-violet-500',
  },
  {
    year: '2024',
    title: 'SGE Ready',
    description: 'First platform optimized for Search Generative Experience',
    icon: Sparkles,
    gradient: 'from-pink-600 to-rose-500',
  },
];

// Awards and recognition
const awards = [
  { name: 'Best SEO Platform 2024', org: 'Search Engine Journal', gradient: 'from-yellow-600 to-orange-500' },
  { name: 'Fastest Growing SaaS', org: 'SaaS Awards 2023', gradient: 'from-blue-600 to-cyan-500' },
  { name: 'Innovation in AI', org: 'TechCrunch Disrupt', gradient: 'from-purple-600 to-pink-500' },
  { name: 'Customer Choice Award', org: 'G2 Crowd', gradient: 'from-green-600 to-emerald-500' },
];

// Office locations
const offices = [
  { city: 'San Francisco', country: 'USA', type: 'Headquarters' },
  { city: 'New York', country: 'USA', type: 'Sales Office' },
  { city: 'London', country: 'UK', type: 'EMEA HQ' },
  { city: 'Singapore', country: 'Singapore', type: 'APAC HQ' },
  { city: 'São Paulo', country: 'Brazil', type: 'LATAM HQ' },
];

export default function AboutPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

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
                  {/* CHANGE #2: Replaced <img> with <Image> */}
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
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Pricing
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
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
                  className="text-sm font-medium text-foreground relative group"
                >
                  About
                  <span className="absolute -bottom-1 left-0 w-full h-0.5 bg-primary" />
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
      <section className="relative min-h-[70vh] flex items-center justify-center overflow-hidden pt-20">
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
          <SEOOrb className="scale-150" colorTheme="blue" />
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
              <Building2 className="mr-1 h-3 w-3" />
              About SerpTank
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Empowering Businesses to</span>
            <span className="block text-gradient-electric mt-2">Master Search</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-16 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {/* CHANGE #3: Escaped the apostrophe */}
            We&apos;re on a mission to democratize enterprise-grade SEO tools,
            making advanced search optimization accessible to businesses of all sizes.
          </motion.p>

          <motion.div 
            className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            {companyStats.map((stat, index) => (
              <motion.div 
                key={index} 
                className="text-center"
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="text-4xl sm:text-5xl font-bold text-gradient mb-2">
                  <AnimatedCounter value={stat.value} />
                </div>
                <div className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Mission Section */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-4xl sm:text-5xl font-bold mb-8">
                Our <span className="text-gradient">Mission</span>
              </h2>
              <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                To transform how businesses approach SEO by combining advanced technology 
                with actionable insights, enabling data-driven decisions that drive real growth.
              </p>
              <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
                We believe every business deserves access to the same powerful SEO tools 
                that Fortune 500 companies use, without the enterprise complexity or cost.
              </p>
              <div className="space-y-6">
                {[
                  { icon: CheckCircle2, title: 'Accessibility', desc: 'Making enterprise tools available to all businesses' },
                  { icon: Lightbulb, title: 'Innovation', desc: 'Pioneering AI-driven SEO solutions' },
                  { icon: Target, title: 'Results', desc: 'Focusing on measurable business outcomes' }
                ].map((item, index) => (
                  <motion.div 
                    key={index}
                    className="flex items-start space-x-4"
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center">
                      <item.icon className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg mb-2">{item.title}</h3>
                      <p className="text-muted-foreground">{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
            <motion.div 
              className="relative"
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="relative aspect-square bg-gradient-to-br from-primary/10 via-accent/10 to-transparent rounded-3xl flex items-center justify-center overflow-hidden">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
                  className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/20"
                />
                <Target className="h-40 w-40 text-primary relative z-10" />
              </div>
              <motion.div
                whileHover={{ y: -5 }}
                className="absolute -bottom-6 -right-6 card-float"
              >
                <Card className="bg-card/90 backdrop-blur-sm border-border/50">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <Trophy className="h-10 w-10 text-yellow-500 relative z-10" />
                        <div className="absolute inset-0 bg-yellow-500/20 blur-xl" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">5,000+</div>
                        <div className="text-sm text-muted-foreground">Happy Customers</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Core Values */}
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
              Our <span className="text-gradient-neon">Core Values</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              The principles that guide everything we do
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {coreValues.map((value, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group"
              >
                <Card className="h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative">
                    <div className={`w-16 h-16 bg-gradient-to-br ${value.gradient} rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                      <value.icon className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-xl">{value.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="relative">
                    <p className="text-muted-foreground">{value.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Leadership Team */}
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
              <span className="text-gradient">Leadership</span> Team
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Led by industry veterans with decades of combined experience
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {leadershipTeam.map((member, index) => (
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
                    <motion.div 
                      className="text-7xl mb-6"
                      whileHover={{ scale: 1.1 }}
                      transition={{ type: "spring", stiffness: 300 }}
                    >
                      {member.image}
                    </motion.div>
                    <CardTitle className="text-xl">{member.name}</CardTitle>
                    <CardDescription className="text-base font-medium text-primary">
                      {member.role}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative">
                    <p className="text-sm text-muted-foreground">{member.bio}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Company Timeline */}
      <section className="relative section-padding bg-gray-50/40 dark:bg-gray-950/40">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Our <span className="text-gradient-electric">Journey</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              From startup to industry leader in 5 years
            </p>
          </motion.div>

          <div className="relative max-w-4xl mx-auto">
            <div className="absolute left-1/2 transform -translate-x-1/2 h-full w-0.5 bg-gradient-to-b from-primary via-accent to-destructive"></div>
            <div className="space-y-16">
              {milestones.map((milestone, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: index % 2 === 0 ? -50 : 50 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  className={`flex items-center ${
                    index % 2 === 0 ? 'justify-start' : 'justify-end'
                  }`}
                >
                  <motion.div 
                    className={`w-5/12 ${index % 2 === 0 ? 'text-right pr-8' : 'text-left pl-8'}`}
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                      <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent" />
                      <CardHeader className="relative">
                        <div className="flex items-center space-x-3 mb-3">
                          <div className={`w-10 h-10 bg-gradient-to-br ${milestone.gradient} rounded-xl flex items-center justify-center`}>
                            <milestone.icon className="h-5 w-5 text-white" />
                          </div>
                          <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                            {milestone.year}
                          </Badge>
                        </div>
                        <CardTitle className="text-xl">{milestone.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="relative">
                        <p className="text-muted-foreground">{milestone.description}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                  <motion.div 
                    className="absolute left-1/2 transform -translate-x-1/2 w-6 h-6 bg-gradient-to-br from-primary to-accent rounded-full shadow-lg shadow-primary/50"
                    whileHover={{ scale: 1.5 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  />
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Awards & Recognition */}
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
              Awards & <span className="text-gradient-neon">Recognition</span>
            </h2>
            <p className="text-xl text-muted-foreground">
              Trusted by industry experts and customers alike
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-6 mb-16">
            {awards.map((award, index) => (
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
                  <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/[0.05] via-orange-500/[0.05] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardContent className="p-8 relative">
                    <motion.div
                      whileHover={{ rotate: 360 }}
                      transition={{ duration: 0.5 }}
                      className="relative inline-block mb-4"
                    >
                      <Award className="h-12 w-12 text-yellow-500 relative z-10" />
                      <div className="absolute inset-0 bg-yellow-500/20 blur-xl" />
                    </motion.div>
                    <h3 className="font-bold text-lg mb-2">{award.name}</h3>
                    <p className="text-sm text-muted-foreground">{award.org}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <motion.div 
            className="text-center"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h3 className="text-2xl font-bold mb-8">Global Presence</h3>
            <div className="flex flex-wrap justify-center gap-4">
              {offices.map((office, index) => (
                <motion.div 
                  key={index} 
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ scale: 1.05 }}
                  className="flex items-center space-x-2 bg-card/80 backdrop-blur-sm border border-border/50 rounded-xl px-6 py-3 shadow-lg"
                >
                  <MapPin className="h-5 w-5 text-primary" />
                  <span className="font-semibold">{office.city}</span>
                  <span className="text-muted-foreground">• {office.type}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
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
            Join Our <span className="text-gradient-electric">Mission</span>
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            {/* CHANGE #4: Escaped the apostrophe */}
            Be part of the team that&apos;s revolutionizing how businesses approach SEO
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => router.push('/careers')}
              >
                View Open Positions
                <ArrowRight className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="glass"
                size="xl"
                onClick={() => router.push('/contact')}
                className="text-xl"
                magneticStrength={0}
              >
                Get in Touch
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
                  {/* CHANGE #5: Replaced <img> with <Image> */}
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