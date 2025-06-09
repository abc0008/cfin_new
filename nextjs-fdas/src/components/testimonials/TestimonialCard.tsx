// src/components/testimonials/TestimonialCard.tsx
import React from 'react';
import Image from 'next/image';
import { Star } from 'lucide-react';

interface TestimonialCardProps {
  quote: string;
  name: string;
  title: string;
  avatarImage: string; // Path to the image in public folder e.g., /assets/TestimonialPortraits/image.jpg
}

const TestimonialCard: React.FC<TestimonialCardProps> = ({ quote, name, title, avatarImage }) => {
  return (
    <div className="relative w-[350px] h-[500px] rounded-2xl overflow-hidden group shadow-lg hover:shadow-xl transition-all duration-300">
      {/* Background Image */}
      <div className="absolute inset-0 w-full h-full">
        <Image 
          src={avatarImage} 
          alt={`${name}'s portrait`} 
          layout="fill" 
          objectFit="cover" 
          className="transition-transform duration-300 group-hover:scale-105"
          priority
        />
      </div>
      
      {/* Gradient Overlay for text readability */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />
      
      {/* Content section positioned at the bottom third of the card */}
      <div className="absolute inset-x-0 bottom-0 p-6 text-white">
        {/* Content container with more space at the top */}
        <div className="flex flex-col space-y-3">
          {/* Star Rating positioned lower on the card */}
          <div className="flex items-center space-x-0.5">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="h-3 w-3 text-brand-lust fill-current" />
            ))}
          </div>
          
          {/* Quote with fixed height */}
          <p className="text-base font-medium h-[72px] overflow-hidden">"{quote}"</p>
          
          {/* Name and title at the bottom */}
          <div className="pt-1">
            <p className="font-semibold text-lg">{name}</p>
            <p className="text-sm text-gray-300">{title}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestimonialCard;
