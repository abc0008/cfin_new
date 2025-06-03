/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		colors: {
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))',
				'6': 'hsl(var(--chart-6))',
				'7': 'hsl(var(--chart-7))',
				'8': 'hsl(var(--chart-8))',
				'up': 'hsl(var(--chart-up))',
				'down': 'hsl(var(--chart-down))',
				'neutral': 'hsl(var(--chart-neutral))'
  			},
			// Professional brand colors for direct usage
			brand: {
				mulberry: '#8f0f56',        // Primary brand color
				lust: '#e5241d',            // Alert/destructive 
				'lust-border': '#e61d24',   // Border variant
				hobgoblin: '#02a88e',       // Secondary/success color
				tamahagane: '#3c3e3e',      // Dark neutral
				'mt-rushmore': '#828282',   // Medium neutral
				pigeon: '#acafaf',          // Light neutral
				'caribbean-blue': '#00bed5', // Accent color
				'white-smoke': '#f6f6f6',   // Light background
				nero: '#242424',            // Dark text
				smokescreen: '#595959'      // Medium text
			}
  		},
		fontFamily: {
			'avenir-pro': ['Avenir Pro', 'Avenir', 'Helvetica Neue', 'Arial', 'sans-serif'],
			'avenir-pro-light': ['Avenir Pro Light', 'Avenir', 'Helvetica Neue', 'Arial', 'sans-serif'],
			'avenir-pro-demi': ['Avenir Pro', 'Avenir', 'Helvetica Neue', 'Arial', 'sans-serif'],
		},
		fontWeight: {
			'light': '300',
			'normal': '400',
			'medium': '500',
			'demi': '600',
			'bold': '700',
		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
		letterSpacing: {
			'tighter': '-0.02em',
			'tight': '-0.01em',
		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: 0
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: 0
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}