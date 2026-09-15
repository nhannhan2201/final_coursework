import pandas as pd
import numpy as np 
import random
from datetime import datetime, timedelta

def generate_sales_data(customers_df, products_df, config):
    random.seed(config['random_seed'])
    np.random.seed(config['random_seed'])

    orders = []
    order_items = []
    payments = []

    end_date = datetime.now()
    start_date = end_date - timedelta(days = config['days_history'])

    schema_change_date = config['schema_change_date']

    customer_ids = customers_df['customer_id'].values
    product_ids = products_df['product_id'].values

    # Cấu hình mốc thời gian Data Drift
    drift_enabled = config.get('drift_enabled', False)
    drift_days = config.get('drift_start_days', 30)
    drift_threshold_date = end_date - timedelta(days=drift_days)
    drift_shifts = config.get('drift_category_shift', {})

    # Chuẩn bị danh sách sản phẩm theo từng ngành hàng để chọn mẫu drift
    category_products = {}
    for cat in products_df['category'].unique():
        category_products[cat] = products_df[products_df['category'] == cat]['product_id'].values

    for i in range(5000):
        order_id = f"ORD_{i:06d}"
        total_order_amount = 0
        cust_id = random.choice(customer_ids)

        order_ts = start_date + timedelta(seconds = random.randint(0, int((end_date - start_date).total_seconds())))

        city = customers_df.loc[customers_df['customer_id']==cust_id, 'city'].values[0]

        if order_ts < schema_change_date:
            shipping_method = None
            coupon_code = None
        else:
            shipping_method = random.choice(['Standard', 'Express'])
            coupon_code = random.choice([None, 'DISCOUNT10', 'DISCOUNT20', 'FREESHIP'])

        orders.append({
            'order_id': order_id,
            'customer_id': cust_id,
            'order_ts': order_ts,
            'status': random.choice(['Delivered', 'Cancelled', 'Shipped']),
            'city': city,
            'shipping_method': shipping_method,
            'coupon_code': coupon_code
        })

        # Kiểm tra xem đơn hàng rơi vào thời kỳ Data Drift (30 ngày gần đây) hay không
        is_in_drift_period = drift_enabled and (order_ts >= drift_threshold_date)

        for j in range(random.randint(1, 3)):
            if is_in_drift_period and drift_shifts:
                # Kích hoạt Data Drift: Chọn danh mục theo trọng số drift (VD: Fashion 70%, Electronics 10%)
                cats = list(drift_shifts.keys())
                weights = [drift_shifts[c] for c in cats]
                total_w = sum(weights)
                norm_weights = [w / total_w for w in weights]
                chosen_cat = np.random.choice(cats, p=norm_weights)
                
                # Chọn ngẫu nhiên sản phẩm thuộc danh mục đã chọn
                available_prods = category_products.get(chosen_cat, product_ids)
                prod_id = np.random.choice(available_prods)
            else:
                # Baseline thông thường: Chọn ngẫu nhiên sản phẩm
                prod_id = np.random.choice(product_ids)

            # Lấy giá gốc của sản phẩm từ bảng Products
            unit_price = products_df.loc[products_df['product_id'] == prod_id, 'base_price'].values[0]
            quantity = random.randint(1, 5)
            line_total = unit_price * quantity

            total_order_amount += line_total

            order_items.append({
                'order_item_id': f"ITEM_{order_id}_{j}",
                'order_id': order_id,
                'product_id': prod_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_amount': 0
            })

        payments.append({
            'payment_id': f"PAY_{i:07d}",
            'order_id': order_id,
            'payment_timestamp': order_ts + timedelta(minutes=random.randint(1, 10)),
            'payment_method': random.choice(['Credit Card', 'E-Wallet', 'COD']),
            'amount': round(total_order_amount, 2), # Amount giờ đã khớp với tiền hàng!
            'payment_status': random.choices(['Success', 'Failed'], weights=[0.9, 0.1])[0]
        })

    df_orders = pd.DataFrame(orders)
    df_items = pd.DataFrame(order_items)
    df_payments = pd.DataFrame(payments)

# --- Giải quyết DUPLICATE (2% cho order_items) ---
    n_dup = int(config['nduplicate_rate_offline'] * len(df_items))
    df_dup = df_items.sample(n_dup, random_state=config['random_seed'])
    df_items = pd.concat([df_items, df_dup], ignore_index=True)

    return df_orders, df_items, df_payments

