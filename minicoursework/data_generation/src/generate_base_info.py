import pandas as pd
from faker import Faker
import random

fake = Faker()

def generate_customers(n_customers, skew_ratio_city, seed):
    random.seed(seed)
    
    customers = []
    cities = ['HCMC', 'Hanoi', 'Da Nang', 'Can Tho', 'Hai Phong']
    weights = [skew_ratio_city, 0.0375, 0.0375, 0.0375, 0.0375] # Tổng = 1.0

    for i in range(n_customers):
        customers.append({
            'customer_id': f"CUST_{i:06d}", # Đảm bảo tính duy nhất (High Cardinality)
            'signup_ts': fake.date_time_between(start_date='-180d', end_date='now'),
            'country': 'Vietnam',
            'city': random.choices(cities, weights=weights)[0], # Gây lệch dữ liệu (Skew)
            'segment': random.choice(['Gold', 'Silver', 'Bronze', 'Standard']),
            'marketing_opt_in': random.choice([True, False])
        })
    
    return pd.DataFrame(customers)


def generate_products(n_products, skew_ratio_category, seed):
    random.seed(seed)
    
    products = []
    categories = ['Electronics', 'Home', 'Beauty', 'Fashion', 'Groceries']
    weights = [skew_ratio_category, 0.05, 0.05, 0.05, 0.05] # Tổng = 1.0
    for i in range(n_products):
        products.append({
            'product_id': f"{i+1:06d}",
            'category': random.choices(categories, weights=weights)[0],
            'brand': fake.company(),
            'base_price': round(random.uniform(10, 1000), 2),
            'is_active': random.choices([True, False], weights = [0.9, 0.1])[0],
            'created_ts': fake.date_time_between(start_date='-1y', end_date='now')
        })

    return pd.DataFrame(products)


def generate_customer_labels(customers_df, churn_rate, seed):
    """
    Sinh bảng nhãn Churn (Ground Truth Label) gồm đúng 2 cột (customer_id, is_churn).
    Phục vụ cho bài toán huấn luyện mô hình Machine Learning Churn Prediction (Theo Rubric).
    """
    random.seed(seed)
    labels = []
    
    for customer_id in customers_df['customer_id']:
        # Sinh nhãn Churn theo tỷ lệ churn_rate (Mặc định 18% khách hàng rời bỏ)
        is_churn = 1 if random.random() < churn_rate else 0
        labels.append({
            'customer_id': customer_id,
            'is_churn': is_churn
        })
        
    return pd.DataFrame(labels)