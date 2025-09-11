'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Command, ArrowRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useSearch, SearchResult, highlightSearchResult } from '@/lib/search-context';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  className?: string;
  placeholder?: string;
  showShortcut?: boolean;
}

export function SearchBar({ 
  className, 
  placeholder = 'Search...', 
  showShortcut = true 
}: SearchBarProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [localQuery, setLocalQuery] = useState('');
  
  const {
    query,
    setQuery,
    results,
    isSearching,
    search,
    setIsAdvancedSearchOpen,
  } = useSearch();

  const handleSearch = async (value: string) => {
    setLocalQuery(value);
    if (value.trim()) {
      setQuery(value);
      await search(value);
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    if (result.url) {
      router.push(result.url);
      setIsOpen(false);
      setLocalQuery('');
      setQuery('');
    }
  };

  const handleAdvancedSearch = () => {
    setIsAdvancedSearchOpen(true);
    setIsOpen(false);
  };

  // Close popover on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-search-popover]')) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isOpen]);

  const topResults = results.slice(0, 5);

  return (
    <div className={cn('relative', className)} data-search-popover>
      <Popover open={isOpen && results.length > 0}>
        <PopoverTrigger asChild>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              ref={inputRef}
              type="search"
              placeholder={placeholder}
              value={localQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className={cn(
                'pl-9 pr-4',
                showShortcut && 'pr-20'
              )}
              onFocus={() => localQuery && setIsOpen(true)}
            />
            {showShortcut && !localQuery && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                  <span className="text-xs">/</span>
                </kbd>
              </div>
            )}
          </div>
        </PopoverTrigger>
        <PopoverContent 
          className="w-[400px] p-0" 
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="max-h-[400px] overflow-y-auto">
            {isSearching ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Searching...
              </div>
            ) : (
              <>
                {topResults.map((result) => (
                  <Card
                    key={result.id}
                    className="border-0 rounded-none hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleResultClick(result)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">
                            {highlightSearchResult(result.title, query)}
                          </p>
                          {result.description && (
                            <p className="text-xs text-muted-foreground mt-1 truncate">
                              {result.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-2">
                          <Badge variant="outline" className="text-xs">
                            {result.type}
                          </Badge>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {results.length > 5 && (
                  <div className="p-2 border-t">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full"
                      onClick={handleAdvancedSearch}
                    >
                      View all {results.length} results
                      <kbd className="ml-2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                        <Command className="h-3 w-3" />
                        <span>⇧</span>
                        <span>F</span>
                      </kbd>
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}