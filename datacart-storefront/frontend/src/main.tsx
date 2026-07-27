import React, { useCallback, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ArrowRight,
  Award,
  BookOpen,
  ChevronLeft,
  CircleCheckBig,
  CircleX,
  Clock,
  Dumbbell,
  Lamp,
  LoaderCircle,
  Minus,
  Monitor,
  Package,
  Plus,
  Search,
  Shield,
  Shirt,
  ShoppingBag,
  ShoppingCart,
  Star,
  Tag,
  Trash2,
  TriangleAlert,
  Truck,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import './index.css'

type View = 'home' | 'shop' | 'product' | 'cart' | 'orders'
type RuntimeLocation = 'local' | 'docker' | 'production'

interface RuntimeInfo {
  backend: RuntimeLocation
  database: {
    location: 'local-docker' | 'lakebase'
    project: string | null
    branch: string | null
  }
}

const frontendRuntime: RuntimeLocation = import.meta.env.DEV
  ? 'local'
  : import.meta.env.VITE_FRONTEND_RUNTIME === 'docker'
    ? 'docker'
    : 'production'

interface Features {
  reviews_active?: boolean
  loyalty_active?: boolean
  exchange_rates_active?: boolean
  order_priority_active?: boolean
  email_verified_active?: boolean
  orders_available?: boolean
  order_items_available?: boolean
  promotions_active?: boolean
  demand_active?: boolean
}

interface Account {
  id: number
  name: string
  email: string
  loyalty_tier?: string
  loyalty_points?: number
  email_verified?: boolean
}

interface Product {
  id: number
  name: string
  category: string
  price: number
  stock: number
  warehouse?: string
  reorder_level?: number
  avg_rating: number
  review_count: number
  loyalty_points_earned?: number
  badge_text?: string
  discount_pct?: number
  sale_price?: number
}

interface Review {
  reviewer: string
  rating: number
  review_date: string
  comment: string
}

interface FeaturedProducts {
  total_products: number
  total_categories: number
  promo_deals: Product[]
  top_rated: Product[]
  best_sellers: Product[]
  reviews_unavailable: boolean
  best_sellers_unavailable: boolean
}

interface ProductList {
  products: Product[]
  categories: string[]
  total: number
}

interface CartItem extends Product {
  cart_quantity: number
  line_total: number
  in_stock: boolean
}

interface Cart {
  items: CartItem[]
  subtotal: number
  item_count: number
  total_points_earned?: number
  loyalty_tier?: string
}

interface Order {
  id: number
  product: string
  quantity: number
  total: number
  currency: string
  order_date: string
  status: string
  priority?: string
}

interface CheckoutResult {
  message: string
  order_ids: number[]
  points_earned?: number
}

interface CategoryStyle {
  icon: LucideIcon
  gradient: string
  color: string
}

const categoryStyles: Record<string, CategoryStyle> = {
  Electronics: {
    icon: Monitor,
    gradient: 'linear-gradient(135deg, #ebf8ff, #bee3f8)',
    color: '#2b6cb0',
  },
  Clothing: {
    icon: Shirt,
    gradient: 'linear-gradient(135deg, #faf5ff, #e9d8fd)',
    color: '#6b46c1',
  },
  Books: {
    icon: BookOpen,
    gradient: 'linear-gradient(135deg, #fffff0, #fefcbf)',
    color: '#975a16',
  },
  Home: {
    icon: Lamp,
    gradient: 'linear-gradient(135deg, #f0fff4, #c6f6d5)',
    color: '#276749',
  },
  Sports: {
    icon: Dumbbell,
    gradient: 'linear-gradient(135deg, #fff5f5, #fed7d7)',
    color: '#c53030',
  },
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

function formatDate(value?: string) {
  if (!value) return '-'
  return value.includes('T') ? value.split('T')[0] : value.split(' ')[0]
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

function CategoryIcon({ category, size = 32 }: { category: string; size?: number }) {
  const style = categoryStyles[category]
  if (!style) return <Tag size={size} />
  const Icon = style.icon
  return <Icon size={size} style={{ color: style.color }} />
}

function categoryGradient(category: string) {
  return categoryStyles[category]?.gradient || 'linear-gradient(135deg, #f7fafc, #edf2f7)'
}

function RatingStars({ rating, size = 14 }: { rating: number; size?: number }) {
  return (
    <span className="stars">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={star <= Math.round(rating) ? 'star-filled' : 'star-empty'}
        />
      ))}
    </span>
  )
}

function StockBadge({ stock }: { stock: number }) {
  if (stock === 0) {
    return (
      <span className="badge badge-red">
        <CircleX size={12} /> Out of Stock
      </span>
    )
  }
  if (stock <= 10) {
    return (
      <span className="badge badge-amber">
        <TriangleAlert size={12} /> Low Stock ({stock})
      </span>
    )
  }
  return (
    <span className="badge badge-green">
      <CircleCheckBig size={12} /> In Stock
    </span>
  )
}

function OrderStatusBadge({ status }: { status: string }) {
  const icons: Record<string, LucideIcon> = {
    pending: Clock,
    confirmed: CircleCheckBig,
    shipped: Truck,
    delivered: Package,
    cancelled: CircleX,
  }
  const classes: Record<string, string> = {
    pending: 'badge-amber',
    confirmed: 'badge-blue',
    shipped: 'badge-purple',
    delivered: 'badge-green',
    cancelled: 'badge-red',
  }
  const Icon = icons[status] || Clock
  return (
    <span className={`badge ${classes[status] || 'badge-gray'}`}>
      <Icon size={12} /> {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority?: string }) {
  if (!priority) return null
  const classes: Record<string, string> = {
    high: 'badge-red',
    medium: 'badge-amber',
    normal: 'badge-gray',
  }
  return (
    <span className={`badge ${classes[priority] || 'badge-gray'}`}>
      <Zap size={12} /> {priority}
    </span>
  )
}

function LoyaltyTierBadge({ tier }: { tier: string }) {
  const classes: Record<string, string> = {
    Bronze: 'badge-amber',
    Silver: 'badge-gray',
    Gold: 'badge-amber',
    Platinum: 'badge-purple',
  }
  return (
    <span className={`badge ${classes[tier] || 'badge-gray'}`}>
      <Award size={12} /> {tier}
    </span>
  )
}

function PromoBadge({ text, discount }: { text: string; discount: number }) {
  return (
    <div className="promo-badge">
      <span>{text}</span>
      <span>-{discount}%</span>
    </div>
  )
}

function PriceDisplay({ price, salePrice }: { price: number; salePrice?: number }) {
  return salePrice && salePrice < price ? (
    <div className="price-display">
      <span className="price-original">{formatCurrency(price)}</span>
      <span className="price-sale">{formatCurrency(salePrice)}</span>
    </div>
  ) : (
    <span className="product-card-price">{formatCurrency(price)}</span>
  )
}

function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spinner" size={20} /> Loading...
    </div>
  )
}

function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onClose, 3000)
    return () => window.clearTimeout(timer)
  }, [onClose])

  return (
    <div className="toast">
      <CircleCheckBig size={16} />
      <span>{message}</span>
      <button onClick={onClose} className="toast-close">
        <X size={14} />
      </button>
    </div>
  )
}

function ProductCard({
  product,
  features,
  onClick,
}: {
  product: Product
  features: Features | null
  onClick: () => void
}) {
  const showRating = features?.reviews_active && product.review_count > 0
  return (
    <div className="product-card" onClick={onClick}>
      <div
        className="product-card-img"
        style={{ background: categoryGradient(product.category), position: 'relative' }}
      >
        <CategoryIcon category={product.category} size={36} />
        <span className="product-card-category">{product.category}</span>
        {product.badge_text && product.discount_pct && (
          <PromoBadge text={product.badge_text} discount={product.discount_pct} />
        )}
      </div>
      <div className="product-card-body">
        <h3>{product.name}</h3>
        {showRating && (
          <div className="product-card-rating">
            <RatingStars rating={product.avg_rating} size={12} />
            <span className="text-muted">({product.review_count})</span>
          </div>
        )}
        <div className="product-card-footer">
          <PriceDisplay price={product.price} salePrice={product.sale_price} />
          <StockBadge stock={product.stock} />
        </div>
        {product.loyalty_points_earned != null && product.loyalty_points_earned > 0 && (
          <div className="loyalty-earn">
            <Award size={12} /> Earn {product.loyalty_points_earned} pts
          </div>
        )}
      </div>
    </div>
  )
}

function HomePage({
  features,
  account,
  onNavigate,
  onViewProduct,
}: {
  features: Features | null
  account: Account | null
  onNavigate: (view: View) => void
  onViewProduct: (productId: number) => void
}) {
  const [featured, setFeatured] = useState<FeaturedProducts | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/shop/featured')
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`)
        return response.json() as Promise<FeaturedProducts>
      })
      .then(setFeatured)
      .catch((cause) => setError(`Store unavailable: ${errorMessage(cause)}`))
  }, [])

  if (error) {
    return (
      <div className="error-page">
        <TriangleAlert size={48} />
        <h2>Store Unavailable</h2>
        <p>{error}</p>
        <p className="error-hint">The database may be down. Check the Lakebase project status.</p>
      </div>
    )
  }
  if (!featured) return <Loading />

  return (
    <>
      <div className="hero">
        <div className="hero-content">
          <h1>Spring Sale is Here!</h1>
          <p>
            Browse {featured.total_products} products across {featured.total_categories} categories
          </p>
          <button className="btn btn-primary btn-lg" onClick={() => onNavigate('shop')}>
            Shop Now <ArrowRight size={18} />
          </button>
        </div>
      </div>

      {features?.loyalty_active && (
        <div className="loyalty-banner">
          <div className="loyalty-banner-content">
            <Award size={24} />
            <div>
              <h3>Loyalty Program Active!</h3>
              <p>
                Earn points on every purchase.{' '}
                {account?.loyalty_tier
                  ? `You're a ${account.loyalty_tier} member with ${account.loyalty_points ?? 0} points!`
                  : 'Shop to earn rewards!'}
              </p>
            </div>
          </div>
        </div>
      )}

      {featured.promo_deals && featured.promo_deals.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>
              <Zap size={20} /> Spring Sale Deals
            </h2>
            <button className="btn btn-ghost" onClick={() => onNavigate('shop')}>
              View All
            </button>
          </div>
          <div className="product-grid">
            {featured.promo_deals.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                features={features}
                onClick={() => onViewProduct(product.id)}
              />
            ))}
          </div>
        </section>
      )}

      {!featured.reviews_unavailable && featured.top_rated.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>
              <Star size={20} /> Top Rated
            </h2>
            <button className="btn btn-ghost" onClick={() => onNavigate('shop')}>
              View All
            </button>
          </div>
          <div className="product-grid">
            {featured.top_rated.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                features={features}
                onClick={() => onViewProduct(product.id)}
              />
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-header">
          <h2>
            <ShoppingBag size={20} /> Best Sellers
          </h2>
          <button className="btn btn-ghost" onClick={() => onNavigate('shop')}>
            View All
          </button>
        </div>
        {featured.best_sellers_unavailable ? (
          <div className="section-unavailable">
            <TriangleAlert size={20} />
            <p>Best sellers data is temporarily unavailable.</p>
          </div>
        ) : (
          <div className="product-grid">
            {featured.best_sellers.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                features={features}
                onClick={() => onViewProduct(product.id)}
              />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function ShopPage({
  features,
  onViewProduct,
  onAddToCart,
}: {
  features: Features | null
  onViewProduct: (productId: number) => void
  onAddToCart: (productId: number) => void
}) {
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadProducts = useCallback(() => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (search) params.set('search', search)
    fetch(`/api/shop/products?${params}`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`)
        return response.json() as Promise<ProductList>
      })
      .then((result) => {
        setProducts(result.products)
        setCategories(result.categories)
        setLoading(false)
      })
      .catch((cause) => {
        setError(errorMessage(cause))
        setLoading(false)
      })
  }, [category, search])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  if (error) {
    return (
      <div className="error-page">
        <TriangleAlert size={48} />
        <h2>Cannot load products</h2>
        <p>{error}</p>
      </div>
    )
  }

  const showRatings = features?.reviews_active
  return (
    <>
      <div className="page-header">
        <h2>Shop All Products</h2>
      </div>
      <div className="shop-controls">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="category-pills">
          <button
            className={`pill ${category === '' ? 'pill-active' : ''}`}
            onClick={() => setCategory('')}
          >
            All
          </button>
          {categories.map((value) => (
            <button
              key={value}
              className={`pill ${category === value ? 'pill-active' : ''}`}
              onClick={() => setCategory(value)}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <Loading />
      ) : (
        <div className="product-grid">
          {products.map((product) => (
            <div className="product-card" key={product.id}>
              <div
                className="product-card-img"
                style={{ background: categoryGradient(product.category), position: 'relative' }}
                onClick={() => onViewProduct(product.id)}
              >
                <CategoryIcon category={product.category} size={36} />
                <span className="product-card-category">{product.category}</span>
                {product.badge_text && product.discount_pct && (
                  <PromoBadge text={product.badge_text} discount={product.discount_pct} />
                )}
              </div>
              <div className="product-card-body">
                <h3 onClick={() => onViewProduct(product.id)}>{product.name}</h3>
                {showRatings && product.review_count > 0 && (
                  <div className="product-card-rating">
                    <RatingStars rating={product.avg_rating} size={12} />
                    <span className="text-muted">({product.review_count})</span>
                  </div>
                )}
                <div className="product-card-footer">
                  <PriceDisplay price={product.price} salePrice={product.sale_price} />
                  <StockBadge stock={product.stock} />
                </div>
                {product.loyalty_points_earned != null && product.loyalty_points_earned > 0 && (
                  <div className="loyalty-earn">
                    <Award size={12} /> Earn {product.loyalty_points_earned} pts
                  </div>
                )}
                <button
                  className="btn btn-primary btn-sm btn-full"
                  disabled={product.stock === 0}
                  onClick={(event) => {
                    event.stopPropagation()
                    onAddToCart(product.id)
                  }}
                >
                  {product.stock === 0 ? 'Out of Stock' : 'Add to Cart'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function ProductDetailPage({
  productId,
  features,
  onBack,
  onAddToCart,
}: {
  productId: number
  features: Features | null
  onBack: () => void
  onAddToCart: (productId: number) => void
}) {
  const [product, setProduct] = useState<Product | null>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`/api/shop/products/${productId}`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`)
        return response.json() as Promise<{ product: Product; reviews: Review[] }>
      })
      .then((result) => {
        setProduct(result.product)
        setReviews(result.reviews)
      })
      .catch((cause) => setError(errorMessage(cause)))
  }, [productId])

  if (error) {
    return (
      <div className="error-page">
        <TriangleAlert size={48} />
        <h2>Product not found</h2>
        <p>{error}</p>
        <button className="btn btn-ghost" onClick={onBack}>
          <ChevronLeft size={16} /> Back to shop
        </button>
      </div>
    )
  }
  if (!product) return <Loading />

  const showReviews = features?.reviews_active
  return (
    <>
      <button className="btn btn-ghost back-btn" onClick={onBack}>
        <ChevronLeft size={16} /> Back to shop
      </button>
      <div className="product-detail">
        <div
          className="product-detail-img"
          style={{ background: categoryGradient(product.category) }}
        >
          <CategoryIcon category={product.category} size={72} />
          <span
            className="product-detail-category"
            style={{ color: categoryStyles[product.category]?.color }}
          >
            {product.category}
          </span>
        </div>
        <div className="product-detail-info">
          <h1>{product.name}</h1>
          {showReviews && product.review_count > 0 && (
            <div className="product-detail-rating">
              <RatingStars rating={product.avg_rating} size={18} />
              <span>{product.avg_rating} / 5</span>
              <span className="text-muted">({product.review_count} reviews)</span>
            </div>
          )}
          {product.sale_price ? (
            <div className="product-detail-price">
              <span className="price-original-lg">{formatCurrency(product.price)}</span>
              <span className="price-sale-lg">{formatCurrency(product.sale_price)}</span>
              <span className="badge badge-red">
                {product.badge_text} -{product.discount_pct}%
              </span>
            </div>
          ) : (
            <div className="product-detail-price">{formatCurrency(product.price)}</div>
          )}
          {product.loyalty_points_earned != null && product.loyalty_points_earned > 0 && (
            <div className="loyalty-earn-lg">
              <Award size={16} /> Earn {product.loyalty_points_earned} loyalty points with this
              purchase
            </div>
          )}
          <div className="product-detail-stock">
            <StockBadge stock={product.stock} />
            {product.warehouse && (
              <span className="text-muted">Warehouse: {product.warehouse}</span>
            )}
          </div>
          <button
            className="btn btn-primary btn-lg"
            disabled={product.stock === 0}
            onClick={() => onAddToCart(product.id)}
          >
            <ShoppingCart size={18} />
            {product.stock === 0 ? 'Out of Stock' : 'Add to Cart'}
          </button>
        </div>
      </div>

      {showReviews && (
        <section className="section">
          <h2>Customer Reviews ({reviews.length})</h2>
          {reviews.length === 0 ? (
            <p className="text-muted">No reviews yet.</p>
          ) : (
            <div className="reviews-list">
              {reviews.map((review, index) => (
                <div className="review-card" key={index}>
                  <div className="review-header">
                    <strong>{review.reviewer}</strong>
                    <RatingStars rating={review.rating} size={12} />
                    <span className="text-muted">{formatDate(review.review_date)}</span>
                  </div>
                  <p>{review.comment}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </>
  )
}

function CartPage({
  onNavigate,
  onCheckout,
}: {
  features: Features | null
  onNavigate: (view: View) => void
  onCheckout: () => Promise<void>
}) {
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')

  const loadCart = useCallback(() => {
    setLoading(true)
    fetch('/api/cart')
      .then((response) => response.json() as Promise<Cart>)
      .then((result) => {
        setCart(result)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadCart()
  }, [loadCart])

  const updateQuantity = (productId: number, quantity: number) => {
    fetch('/api/cart/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId, quantity }),
    }).then(loadCart)
  }

  const clearCart = () => {
    fetch('/api/cart/clear', { method: 'POST' }).then(loadCart)
  }

  const checkout = async () => {
    setProcessing(true)
    setError('')
    try {
      await onCheckout()
      loadCart()
    } catch (cause) {
      const message = errorMessage(cause) || 'Checkout failed'
      setError(
        message.includes('unavailable') || message.includes('503')
          ? 'Checkout is temporarily unavailable — the orders system is being recovered. Your cart is safe!'
          : message,
      )
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <Loading />
  return (
    <>
      <div className="page-header">
        <h2>
          <ShoppingCart size={22} /> Your Cart
        </h2>
        {cart && cart.items.length > 0 && (
          <button className="btn btn-ghost btn-sm" onClick={clearCart}>
            <Trash2 size={14} /> Clear Cart
          </button>
        )}
      </div>
      {error && (
        <div className="error-banner">
          <TriangleAlert size={16} /> {error}
        </div>
      )}
      {!cart || cart.items.length === 0 ? (
        <div className="empty-state">
          <ShoppingCart size={48} />
          <h3>Your cart is empty</h3>
          <p>Browse our products and add something!</p>
          <button className="btn btn-primary" onClick={() => onNavigate('shop')}>
            Start Shopping <ArrowRight size={16} />
          </button>
        </div>
      ) : (
        <>
          <div className="cart-items">
            {cart.items.map((item) => (
              <div className={`cart-item ${item.in_stock ? '' : 'cart-item-oos'}`} key={item.id}>
                <div className="cart-item-info">
                  <h3>{item.name}</h3>
                  <span className="text-muted">{item.category}</span>
                  <span className="cart-item-price">{formatCurrency(item.price)} each</span>
                  {!item.in_stock && (
                    <span className="badge badge-red">
                      <TriangleAlert size={12} /> Not enough stock
                    </span>
                  )}
                  {item.loyalty_points_earned != null && item.loyalty_points_earned > 0 && (
                    <span className="loyalty-earn">
                      <Award size={12} /> +{item.loyalty_points_earned} pts
                    </span>
                  )}
                </div>
                <div className="cart-item-controls">
                  <button
                    className="btn btn-icon"
                    onClick={() => updateQuantity(item.id, item.cart_quantity - 1)}
                  >
                    <Minus size={14} />
                  </button>
                  <span className="cart-item-qty">{item.cart_quantity}</span>
                  <button
                    className="btn btn-icon"
                    onClick={() => updateQuantity(item.id, item.cart_quantity + 1)}
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    className="btn btn-icon btn-danger"
                    onClick={() => updateQuantity(item.id, 0)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="cart-item-total">{formatCurrency(item.line_total)}</div>
              </div>
            ))}
          </div>
          <div className="cart-summary">
            <div className="cart-summary-row">
              <span>Subtotal ({cart.item_count} items)</span>
              <span className="cart-summary-total">{formatCurrency(cart.subtotal)}</span>
            </div>
            {cart.total_points_earned != null && cart.total_points_earned > 0 && (
              <div className="cart-loyalty-summary">
                <span>
                  <Award size={14} /> You'll earn {cart.total_points_earned} loyalty points
                </span>
                {cart.loyalty_tier && <LoyaltyTierBadge tier={cart.loyalty_tier} />}
              </div>
            )}
            <button
              className="btn btn-primary btn-lg btn-full"
              disabled={processing || cart.items.some((item) => !item.in_stock)}
              onClick={checkout}
            >
              {processing ? (
                <>
                  <LoaderCircle className="spinner" size={16} /> Processing...
                </>
              ) : (
                'Place Order'
              )}
            </button>
          </div>
        </>
      )}
    </>
  )
}

function OrdersPage({
  onNavigate,
}: {
  features: Features | null
  onNavigate: (view: View) => void
}) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [serviceUnavailable, setServiceUnavailable] = useState(false)

  useEffect(() => {
    fetch('/api/orders')
      .then((response) => {
        if (response.status === 503) {
          setServiceUnavailable(true)
          throw new Error('Service unavailable')
        }
        if (!response.ok) throw new Error(`${response.status}`)
        return response.json() as Promise<{ orders: Order[] }>
      })
      .then((result) => {
        setOrders(result.orders)
        setLoading(false)
      })
      .catch((cause) => {
        setError(errorMessage(cause))
        setLoading(false)
      })
  }, [])

  if (serviceUnavailable) {
    return (
      <div className="error-page">
        <TriangleAlert size={48} />
        <h2>Orders Service Unavailable</h2>
        <p>The orders system is temporarily down due to a database incident.</p>
        <p className="text-muted">
          Products and browsing still work — your data is being recovered.
        </p>
        <button className="btn btn-primary" onClick={() => onNavigate('shop')}>
          Continue Shopping <ArrowRight size={16} />
        </button>
      </div>
    )
  }
  if (error) {
    return (
      <div className="error-page">
        <TriangleAlert size={48} />
        <h2>Cannot load orders</h2>
        <p>{error}</p>
      </div>
    )
  }
  if (loading) return <Loading />

  return (
    <>
      <div className="page-header">
        <h2>
          <Package size={22} /> Your Orders
        </h2>
      </div>
      {orders.length === 0 ? (
        <div className="empty-state">
          <Package size={48} />
          <h3>No orders yet</h3>
          <p>Place your first order to see it here.</p>
        </div>
      ) : (
        <div className="orders-list">
          {orders.map((order) => (
            <div className="order-card" key={order.id}>
              <div className="order-card-header">
                <span className="order-id">Order #{order.id}</span>
                <div className="order-badges">
                  {order.priority && <PriorityBadge priority={order.priority} />}
                  <OrderStatusBadge status={order.status} />
                </div>
              </div>
              <div className="order-card-body">
                <span className="order-product">{order.product}</span>
                <span className="text-muted">Qty: {order.quantity}</span>
                <span className="order-total">
                  {formatCurrency(order.total)} {order.currency}
                </span>
                <span className="text-muted">{formatDate(order.order_date)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function RuntimeIndicator({ runtime }: { runtime: RuntimeInfo | null }) {
  const displayLocation = (location: RuntimeLocation) =>
    location.charAt(0).toUpperCase() + location.slice(1)
  const frontendValue = displayLocation(frontendRuntime)
  const backendValue = runtime ? displayLocation(runtime.backend) : 'Unavailable'
  const databaseValue =
    runtime?.database.location === 'lakebase'
      ? `Lakebase · ${runtime.database.branch} · ${runtime.database.project}`
      : runtime
        ? 'Local Docker'
        : 'Unavailable'

  return (
    <div className="runtime-indicator" aria-label="Runtime locations">
      <span className="runtime-chip" title={`Frontend: ${frontendValue}`}>
        <span className="runtime-chip-label">Frontend</span>
        <strong>{frontendValue}</strong>
      </span>
      <span className="runtime-chip" title={`Backend: ${backendValue}`}>
        <span className="runtime-chip-label">Backend</span>
        <strong>{backendValue}</strong>
      </span>
      <span
        className="runtime-chip runtime-chip-database"
        data-tooltip={`Database: ${databaseValue}`}
        aria-label={`Database: ${databaseValue}`}
        tabIndex={0}
      >
        <span className="runtime-chip-label">Database</span>
        <strong className="runtime-chip-value">{databaseValue}</strong>
      </span>
    </div>
  )
}

function App() {
  const [view, setView] = useState<View>('home')
  const [selectedProductId, setSelectedProductId] = useState(0)
  const [cartCount, setCartCount] = useState(0)
  const [toast, setToast] = useState('')
  const [features, setFeatures] = useState<Features | null>(null)
  const [account, setAccount] = useState<Account | null>(null)
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null)

  const refreshCart = useCallback(() => {
    fetch('/api/cart')
      .then((response) => response.json() as Promise<Cart>)
      .then((result) => setCartCount(result.item_count))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const loadFeatures = () => {
      fetch('/api/features')
        .then((response) => response.json() as Promise<Features>)
        .then(setFeatures)
        .catch(() => {})
    }
    loadFeatures()
    const timer = window.setInterval(loadFeatures, 30000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (features?.loyalty_active || features?.email_verified_active) {
      fetch('/api/account')
        .then((response) => response.json() as Promise<Account>)
        .then(setAccount)
        .catch(() => {})
    } else {
      setAccount(null)
    }
  }, [features])

  useEffect(() => {
    refreshCart()
  }, [refreshCart])

  useEffect(() => {
    fetch('/api/runtime')
      .then((response) => {
        if (!response.ok) throw new Error('Runtime metadata unavailable')
        return response.json() as Promise<RuntimeInfo>
      })
      .then(setRuntime)
      .catch(() => setRuntime(null))
  }, [])

  const navigate = (nextView: View) => {
    setView(nextView)
    window.scrollTo(0, 0)
  }

  const viewProduct = (productId: number) => {
    setSelectedProductId(productId)
    setView('product')
    window.scrollTo(0, 0)
  }

  const addToCart = (productId: number) => {
    fetch('/api/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId, quantity: 1 }),
    })
      .then((response) => response.json() as Promise<{ message?: string }>)
      .then((result) => {
        setToast(result.message || 'Added to cart')
        refreshCart()
      })
      .catch(() => setToast('Failed to add to cart'))
  }

  const checkout = async () => {
    const response = await fetch('/api/orders/checkout', { method: 'POST' })
    const result = (await response.json()) as CheckoutResult & { detail?: string }
    if (!response.ok) throw new Error(result.detail || 'Checkout failed')
    setToast(
      result.points_earned
        ? `${result.message} You earned ${result.points_earned} loyalty points!`
        : result.message,
    )
    refreshCart()
    if (features?.loyalty_active) {
      fetch('/api/account')
        .then((accountResponse) => accountResponse.json() as Promise<Account>)
        .then(setAccount)
        .catch(() => {})
    }
    navigate('orders')
  }

  return (
    <div className="app">
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="navbar-brand" onClick={() => navigate('home')}>
            <ShoppingBag size={24} />
            <span>DataCart</span>
          </div>
          <div className="navbar-links">
            <button
              className={`nav-link ${view === 'home' ? 'active' : ''}`}
              onClick={() => navigate('home')}
            >
              Home
            </button>
            <button
              className={`nav-link ${view === 'shop' ? 'active' : ''}`}
              onClick={() => navigate('shop')}
            >
              Shop
            </button>
            <button
              className={`nav-link ${view === 'orders' ? 'active' : ''}`}
              onClick={() => navigate('orders')}
            >
              Orders
            </button>
          </div>
          <RuntimeIndicator runtime={runtime} />
          <div className="navbar-right">
            {account?.loyalty_tier && (
              <div className="nav-loyalty">
                <LoyaltyTierBadge tier={account.loyalty_tier} />
                <span className="loyalty-points">{account.loyalty_points ?? 0} pts</span>
              </div>
            )}
            {account?.email_verified && (
              <span className="badge badge-green">
                <Shield size={12} /> Verified
              </span>
            )}
            <button className="nav-cart" onClick={() => navigate('cart')}>
              <ShoppingCart size={20} />
              {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
            </button>
          </div>
        </div>
      </nav>

      <main className="main">
        {view === 'home' && (
          <HomePage
            features={features}
            account={account}
            onNavigate={navigate}
            onViewProduct={viewProduct}
          />
        )}
        {view === 'shop' && (
          <ShopPage
            features={features}
            onViewProduct={viewProduct}
            onAddToCart={addToCart}
          />
        )}
        {view === 'product' && (
          <ProductDetailPage
            productId={selectedProductId}
            features={features}
            onBack={() => navigate('shop')}
            onAddToCart={addToCart}
          />
        )}
        {view === 'cart' && (
          <CartPage features={features} onNavigate={navigate} onCheckout={checkout} />
        )}
        {view === 'orders' && <OrdersPage features={features} onNavigate={navigate} />}
      </main>

      <footer className="footer">
        <p>
          DataCart Storefront — Powered by <strong>Databricks Lakebase</strong>
        </p>
        <p className="text-muted">Lakebase Branching Workshop Demo</p>
      </footer>

      {toast && <Toast message={toast} onClose={() => setToast('')} />}
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
