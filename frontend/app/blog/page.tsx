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
  BookOpen,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  Filter,
  Heart,
  MessageSquare,
  Search,
  Share2,
  Tag,
  TrendingUp,
  User,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Blog categories
const blogCategories = [
  { id: 'all', name: 'All Posts', count: 47 },
  { id: 'seo-strategy', name: 'SEO Strategy', count: 12 },
  { id: 'technical-seo', name: 'Technical SEO', count: 8 },
  { id: 'content-marketing', name: 'Content Marketing', count: 10 },
  { id: 'ai-insights', name: 'AI & Insights', count: 7 },
  { id: 'case-studies', name: 'Case Studies', count: 6 },
  { id: 'product-updates', name: 'Product Updates', count: 4 },
];

// Sample blog posts
const blogPosts = [
  {
    id: 1,
    title: 'The Future of SEO: How AI is Transforming Search Optimization in 2025',
    excerpt: 'Discover how artificial intelligence is revolutionizing SEO strategies and what it means for businesses looking to stay ahead in search rankings.',
    content: 'The landscape of search engine optimization has undergone dramatic changes with the introduction of AI-powered algorithms...',
    author: {
      name: 'Sarah Chen',
      role: 'CEO & Co-founder',
      avatar: '👩‍💼',
    },
    category: 'ai-insights',
    tags: ['AI', 'SEO Strategy', 'Future Trends', 'Machine Learning'],
    publishedAt: '2025-01-20',
    readTime: 8,
    views: 2847,
    likes: 156,
    comments: 23,
    featured: true,
    image: '🤖',
  },
  {
    id: 2,
    title: 'Complete Guide to Technical SEO Audits: 50+ Checkpoints for 2025',
    excerpt: 'A comprehensive checklist covering everything from Core Web Vitals to mobile optimization, ensuring your site meets modern SEO standards.',
    content: 'Technical SEO forms the foundation of any successful optimization strategy. Without proper technical implementation...',
    author: {
      name: 'Michael Rodriguez',
      role: 'CTO & Co-founder',
      avatar: '👨‍💻',
    },
    category: 'technical-seo',
    tags: ['Technical SEO', 'Website Audit', 'Core Web Vitals', 'Performance'],
    publishedAt: '2025-01-18',
    readTime: 12,
    views: 1923,
    likes: 89,
    comments: 17,
    featured: false,
    image: '⚙️',
  },
  {
    id: 3,
    title: 'How SaaS Company Increased Organic Traffic by 347% in 6 Months',
    excerpt: 'A detailed case study showing how strategic content optimization and technical improvements led to massive organic growth.',
    content: 'When CloudSync approached us, they were struggling with stagnant organic traffic despite having great products...',
    author: {
      name: 'Jennifer Park',
      role: 'VP of Product',
      avatar: '👩‍🔬',
    },
    category: 'case-studies',
    tags: ['Case Study', 'SaaS SEO', 'Content Strategy', 'Growth'],
    publishedAt: '2025-01-15',
    readTime: 10,
    views: 3156,
    likes: 203,
    comments: 31,
    featured: true,
    image: '📈',
  },
  {
    id: 4,
    title: 'Content Clusters vs. Topic Authority: Building SEO-First Content Architecture',
    excerpt: 'Learn how to structure your content for maximum search engine visibility using topic clusters and pillar page strategies.',
    content: 'Content clustering has become one of the most effective strategies for building topical authority...',
    author: {
      name: 'Alex Thompson',
      role: 'Content Marketing Manager',
      avatar: '✍️',
    },
    category: 'content-marketing',
    tags: ['Content Strategy', 'Topic Clusters', 'Content Architecture', 'Authority Building'],
    publishedAt: '2025-01-12',
    readTime: 9,
    views: 1647,
    likes: 124,
    comments: 19,
    featured: false,
    image: '📝',
  },
  {
    id: 5,
    title: 'SGE Optimization: Preparing Your Content for AI-Powered Search Results',
    excerpt: 'Everything you need to know about optimizing for Search Generative Experience and future-proofing your SEO strategy.',
    content: 'Google\'s Search Generative Experience represents the biggest shift in search since the introduction of mobile-first indexing...',
    author: {
      name: 'David Kim',
      role: 'SEO Specialist',
      avatar: '🔍',
    },
    category: 'seo-strategy',
    tags: ['SGE', 'AI Search', 'Future SEO', 'Content Optimization'],
    publishedAt: '2025-01-10',
    readTime: 11,
    views: 2234,
    likes: 167,
    comments: 26,
    featured: false,
    image: '🔮',
  },
  {
    id: 6,
    title: 'New Release: Enhanced AI Recommendations and Real-Time Alerts',
    excerpt: 'Discover the latest SerpTank features including smarter AI insights, instant notifications, and improved competitive analysis.',
    content: 'We\'re excited to announce our biggest platform update yet, featuring enhanced AI capabilities...',
    author: {
      name: 'Product Team',
      role: 'SerpTank',
      avatar: '🚀',
    },
    category: 'product-updates',
    tags: ['Product Update', 'AI Features', 'Real-time Alerts', 'Platform'],
    publishedAt: '2025-01-08',
    readTime: 6,
    views: 1432,
    likes: 78,
    comments: 12,
    featured: false,
    image: '🎉',
  },
  {
    id: 7,
    title: 'Local SEO in 2025: Complete Guide to Dominating Local Search',
    excerpt: 'Master local search optimization with advanced strategies for Google Business Profile, local citations, and geo-targeted content.',
    content: 'Local SEO continues to evolve rapidly, with new features and ranking factors emerging regularly...',
    author: {
      name: 'Maria Gonzalez',
      role: 'Local SEO Expert',
      avatar: '🌍',
    },
    category: 'seo-strategy',
    tags: ['Local SEO', 'Google Business Profile', 'Local Citations', 'Geo-targeting'],
    publishedAt: '2025-01-05',
    readTime: 13,
    views: 1876,
    likes: 112,
    comments: 22,
    featured: false,
    image: '📍',
  },
  {
    id: 8,
    title: 'E-commerce SEO: How Fashion Brand Tripled Revenue Through Search',
    excerpt: 'A comprehensive case study showing how strategic SEO improvements led to massive revenue growth for an online fashion retailer.',
    content: 'When StyleCraft came to us, they were struggling to compete with larger fashion brands in search results...',
    author: {
      name: 'Rachel Liu',
      role: 'E-commerce SEO Consultant',
      avatar: '🛍️',
    },
    category: 'case-studies',
    tags: ['E-commerce SEO', 'Fashion', 'Revenue Growth', 'Product Pages'],
    publishedAt: '2025-01-03',
    readTime: 14,
    views: 2567,
    likes: 189,
    comments: 35,
    featured: false,
    image: '👗',
  },
];

export default function BlogPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  const postsPerPage = 6;
  const totalPages = Math.ceil(blogPosts.length / postsPerPage);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Filter posts based on category and search
  const filteredPosts = blogPosts.filter(post => {
    const matchesCategory = selectedCategory === 'all' || post.category === selectedCategory;
    const matchesSearch = searchQuery === '' || 
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.excerpt.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesCategory && matchesSearch;
  });

  // Paginate filtered posts
  const startIndex = (currentPage - 1) * postsPerPage;
  const paginatedPosts = filteredPosts.slice(startIndex, startIndex + postsPerPage);

  // Get featured posts
  const featuredPosts = blogPosts.filter(post => post.featured);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1); // Reset to first page when searching
  };

  const getCategoryName = (categoryId: string) => {
    const category = blogCategories.find(cat => cat.id === categoryId);
    return category ? category.name : categoryId;
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

      {/* Hero Section with Search */}
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
          <SEOOrb className="scale-150" colorTheme="green" />
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
              <BookOpen className="mr-1 h-3 w-3" />
              SEO Blog & Insights
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">SEO Insights &</span>
            <span className="block text-gradient-electric mt-2">Expert Knowledge</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Discover the latest SEO strategies, industry insights, and expert tips
            to help you dominate search results and grow your business.
          </motion.p>

          {/* Search Bar */}
          <motion.div 
            className="max-w-xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <form onSubmit={handleSearch} className="relative">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search articles, guides, and insights..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 text-base bg-card/80 backdrop-blur-sm border border-border/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                />
              </div>
            </form>
          </motion.div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Featured Articles */}
      {featuredPosts.length > 0 && (
        <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
          <div className="container-width px-6 mx-auto">
            <motion.div 
              className="mb-12"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <div className="flex items-center space-x-3 mb-8">
                <TrendingUp className="h-6 w-6 text-accent" />
                <h2 className="text-3xl font-bold">Featured Articles</h2>
              </div>
            </motion.div>

            <div className="grid lg:grid-cols-2 gap-8">
              {featuredPosts.map((post, index) => (
                <motion.div
                  key={post.id}
                  initial={{ opacity: 0, y: 50 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  whileHover={{ y: -10 }}
                  className="group cursor-pointer"
                  onClick={() => router.push(`/blog/${post.id}`)}
                >
                  <Card className="h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                    <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    
                    {/* Article Image */}
                    <div className="relative h-48 bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center text-6xl">
                      {post.image}
                    </div>
                    
                    <CardHeader className="relative">
                      <div className="flex items-center gap-3 mb-4">
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                          {getCategoryName(post.category)}
                        </Badge>
                        <Badge variant="outline" className="bg-accent/10 text-accent border-accent/20">
                          Featured
                        </Badge>
                      </div>
                      <CardTitle className="text-2xl group-hover:text-primary transition-colors">
                        {post.title}
                      </CardTitle>
                      <CardDescription className="text-base mt-3">
                        {post.excerpt}
                      </CardDescription>
                    </CardHeader>
                    
                    <CardContent className="relative">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-2">
                            <span className="text-2xl">{post.author.avatar}</span>
                            <div>
                              <div className="font-medium text-sm">{post.author.name}</div>
                              <div className="text-xs text-muted-foreground">{post.author.role}</div>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>{post.readTime}min read</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Eye className="h-4 w-4" />
                            <span>{post.views.toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Blog Content */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-4 gap-12">
            {/* Sidebar with Categories */}
            <div className="lg:col-span-1">
              <div className="sticky top-32 space-y-8">
                {/* Categories */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Categories</h3>
                  <div className="space-y-2">
                    {blogCategories.map((category) => (
                      <button
                        key={category.id}
                        onClick={() => {
                          setSelectedCategory(category.id);
                          setCurrentPage(1);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
                          selectedCategory === category.id
                            ? 'bg-primary/10 text-primary'
                            : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
                        }`}
                      >
                        <span>{category.name}</span>
                        <span className="text-xs">{category.count}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Popular Tags */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Popular Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {['AI', 'SEO Strategy', 'Technical SEO', 'Content Marketing', 'Case Study', 'Local SEO'].map((tag) => (
                      <Badge 
                        key={tag}
                        variant="secondary"
                        className="cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors"
                        onClick={() => setSearchQuery(tag)}
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Newsletter Signup */}
                <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg">Stay Updated</CardTitle>
                    <CardDescription>
                      Get the latest SEO insights delivered to your inbox
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <input
                        type="email"
                        placeholder="Enter your email"
                        className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                      />
                      <CTAButton size="sm" className="w-full">
                        Subscribe
                      </CTAButton>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              {/* Results Info */}
              <div className="flex items-center justify-between mb-8">
                <p className="text-muted-foreground">
                  Showing {startIndex + 1}-{Math.min(startIndex + postsPerPage, filteredPosts.length)} of {filteredPosts.length} articles
                  {selectedCategory !== 'all' && (
                    <span> in {getCategoryName(selectedCategory)}</span>
                  )}
                  {searchQuery && (
                    <span> matching "{searchQuery}"</span>
                  )}
                </p>
                <div className="flex items-center space-x-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <select className="text-sm bg-card border border-border rounded-lg px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary/50">
                    <option>Latest First</option>
                    <option>Most Popular</option>
                    <option>Most Commented</option>
                  </select>
                </div>
              </div>

              {/* Articles Grid */}
              <div className="grid md:grid-cols-2 gap-8 mb-12">
                {paginatedPosts.map((post, index) => (
                  <motion.div
                    key={post.id}
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.1 }}
                    whileHover={{ y: -5 }}
                    className="group cursor-pointer"
                    onClick={() => router.push(`/blog/${post.id}`)}
                  >
                    <Card className="h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                      <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                      
                      {/* Article Image */}
                      <div className="relative h-40 bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center text-4xl">
                        {post.image}
                      </div>
                      
                      <CardHeader className="relative">
                        <div className="flex items-center justify-between mb-3">
                          <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                            {getCategoryName(post.category)}
                          </Badge>
                          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            <span>{new Date(post.publishedAt).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <CardTitle className="text-lg group-hover:text-primary transition-colors line-clamp-2">
                          {post.title}
                        </CardTitle>
                        <CardDescription className="text-sm mt-2 line-clamp-3">
                          {post.excerpt}
                        </CardDescription>
                      </CardHeader>
                      
                      <CardContent className="relative">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="text-lg">{post.author.avatar}</span>
                            <div>
                              <div className="font-medium text-xs">{post.author.name}</div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                            <div className="flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{post.readTime}min</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Eye className="h-3 w-3" />
                              <span>{post.views.toLocaleString()}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Heart className="h-3 w-3" />
                              <span>{post.likes}</span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <motion.div
                  className="flex items-center justify-center space-x-2"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                >
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="flex items-center space-x-2 px-4 py-2 text-sm bg-card border border-border rounded-lg hover:bg-primary/5 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    <span>Previous</span>
                  </button>
                  
                  <div className="flex items-center space-x-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-10 h-10 text-sm rounded-lg transition-all ${
                          currentPage === page
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-card border border-border hover:bg-primary/5'
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>
                  
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="flex items-center space-x-2 px-4 py-2 text-sm bg-card border border-border rounded-lg hover:bg-primary/5 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </motion.div>
              )}
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
            Ready to Apply <span className="text-gradient-electric">These Insights</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Turn knowledge into results with SerpTank's AI-powered SEO platform
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
                onClick={() => router.push('/features')}
                className="text-xl"
                magneticStrength={0}
              >
                Explore Features
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
                        className={`transition-colors ${
                          link === 'Blog' 
                            ? 'text-foreground font-medium' 
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
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