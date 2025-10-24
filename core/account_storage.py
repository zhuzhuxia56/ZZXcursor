#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号存储模块
使用 SQLite 数据库管理账号信息
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.crypto import get_crypto_manager
from utils.app_paths import get_database_file

logger = get_logger("account_storage")


class AccountStorage:
    """账号存储管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化账号存储
        
        Args:
            db_path: 数据库文件路径（可选，默认使用用户目录）
        """
        # 使用用户目录的数据库路径
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_database_file()
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.crypto = get_crypto_manager()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建账号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT,
                access_token TEXT,
                refresh_token TEXT,
                session_token TEXT,
                user_id TEXT,
                membership_type TEXT DEFAULT 'free',
                days_remaining INTEGER DEFAULT 0,
                usage_percent REAL DEFAULT 0.0,
                used INTEGER DEFAULT 0,
                limit_value INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                last_refreshed TIMESTAMP,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        ''')
        
        # 数据库迁移：添加 session_token 字段（如果不存在）
        try:
            cursor.execute("SELECT session_token FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 session_token 字段")
            cursor.execute("ALTER TABLE accounts ADD COLUMN session_token TEXT")
            conn.commit()
        
        # 数据库迁移：添加 db_path 字段（如果不存在）
        try:
            cursor.execute("SELECT db_path FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 db_path 字段")
            cursor.execute("ALTER TABLE accounts ADD COLUMN db_path TEXT")
            conn.commit()
        
        # 数据库迁移：添加 token_format 字段（如果不存在）
        try:
            cursor.execute("SELECT token_format FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 token_format 字段")
            cursor.execute("ALTER TABLE accounts ADD COLUMN token_format TEXT")
            conn.commit()
        
        # 数据库迁移：添加 detected_at 字段（如果不存在）
        try:
            cursor.execute("SELECT detected_at FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 detected_at 字段")
            cursor.execute("ALTER TABLE accounts ADD COLUMN detected_at TIMESTAMP")
            conn.commit()
        
        # 数据库迁移：添加 machine_id_json 字段（如果不存在）
        try:
            cursor.execute("SELECT machine_id_json FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 machine_id_json 字段")
            cursor.execute("ALTER TABLE accounts ADD COLUMN machine_id_json TEXT")
            conn.commit()
        
        # 数据库迁移：添加 total_cost 字段（如果不存在）
        try:
            cursor.execute("SELECT total_cost FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 total_cost 字段（真实费用）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN total_cost REAL")
            conn.commit()
        
        # 数据库迁移：添加 total_tokens 字段（如果不存在）
        try:
            cursor.execute("SELECT total_tokens FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 total_tokens 字段（总tokens）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN total_tokens INTEGER")
            conn.commit()
        
        # 数据库迁移：添加 subscription_status 字段（如果不存在）
        try:
            cursor.execute("SELECT subscription_status FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 subscription_status 字段（订阅状态）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN subscription_status TEXT")
            conn.commit()
        
        # 数据库迁移：添加 unpaid_amount 字段（如果不存在）
        try:
            cursor.execute("SELECT unpaid_amount FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 unpaid_amount 字段（实际欠费金额）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN unpaid_amount REAL DEFAULT 0")
            conn.commit()
        
        # 数据库迁移：添加 model_usage_json 字段（如果不存在）
        try:
            cursor.execute("SELECT model_usage_json FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 model_usage_json 字段（模型费用详情）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN model_usage_json TEXT")
            conn.commit()
        
        # ⭐ 数据库迁移：添加 last_refresh_time 字段（增量刷新的时间起点）
        try:
            cursor.execute("SELECT last_refresh_time FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 last_refresh_time 字段（最后刷新时间）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN last_refresh_time TIMESTAMP")
            conn.commit()
        
        # ⭐ 数据库迁移：添加 accumulated_cost 字段（累计总金额）
        try:
            cursor.execute("SELECT accumulated_cost FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 accumulated_cost 字段（累计总金额）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN accumulated_cost REAL DEFAULT 0")
            conn.commit()
        
        # ⭐ 数据库迁移：添加 is_invalid 字段（账号失效标记）
        try:
            cursor.execute("SELECT is_invalid FROM accounts LIMIT 1")
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            logger.info("数据库迁移：添加 is_invalid 字段（失效标记）")
            cursor.execute("ALTER TABLE accounts ADD COLUMN is_invalid INTEGER DEFAULT 0")
            conn.commit()
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn
    
    def add_account(self, account_data: Dict[str, Any]) -> Optional[int]:
        """
        添加新账号
        
        Args:
            account_data: 账号数据字典
            
        Returns:
            Optional[int]: 账号 ID 或 None
        """
        conn = None
        try:
            # 加密敏感字段
            encrypted_data = account_data.copy()
            if 'password' in encrypted_data and encrypted_data['password']:
                encrypted_data['password'] = self.crypto.encrypt(encrypted_data['password'])
            if 'access_token' in encrypted_data and encrypted_data['access_token']:
                encrypted_data['access_token'] = self.crypto.encrypt(encrypted_data['access_token'])
            if 'refresh_token' in encrypted_data and encrypted_data['refresh_token']:
                encrypted_data['refresh_token'] = self.crypto.encrypt(encrypted_data['refresh_token'])
            # ⭐ 加密 session_token（type=web，用于 API 调用）
            if 'session_token' in encrypted_data and encrypted_data['session_token']:
                encrypted_data['session_token'] = self.crypto.encrypt(encrypted_data['session_token'])
            # ⭐ 加密 machine_info（机器码信息）
            if 'machine_info' in encrypted_data and encrypted_data['machine_info']:
                import json
                machine_info_json = json.dumps(encrypted_data['machine_info'])
                encrypted_data['machine_id_json'] = self.crypto.encrypt(machine_info_json)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 插入数据（包含 session_token、db_path 和 machine_id_json）
            cursor.execute('''
                INSERT INTO accounts (
                    email, password, access_token, refresh_token, session_token, user_id,
                    membership_type, days_remaining, usage_percent, used, limit_value, status, db_path, machine_id_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                encrypted_data.get('email'),
                encrypted_data.get('password', ''),
                encrypted_data.get('access_token', ''),
                encrypted_data.get('refresh_token', ''),
                encrypted_data.get('session_token', ''),
                encrypted_data.get('user_id', ''),
                encrypted_data.get('membership_type', 'free'),
                encrypted_data.get('days_remaining', 0),
                encrypted_data.get('usage_percent', 0.0),
                encrypted_data.get('used', 0),
                encrypted_data.get('limit', 1000),
                encrypted_data.get('status', 'active'),
                encrypted_data.get('db_path', ''),
                encrypted_data.get('machine_id_json', '')
            ))
            
            account_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"成功添加账号: {account_data.get('email')} (ID: {account_id})")
            return account_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"账号已存在: {account_data.get('email')}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return None
        except Exception as e:
            logger.error(f"添加账号失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def upsert_account(self, account_data: Dict[str, Any]) -> Optional[int]:
        """
        更新或插入账号（如果存在则更新，不存在则插入）
        
        Args:
            account_data: 账号数据字典
            
        Returns:
            Optional[int]: 账号 ID 或 None
        """
        conn = None
        try:
            email = account_data.get('email')
            if not email:
                logger.error("账号数据缺少 email 字段")
                return None
            
            # 检查账号是否存在
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM accounts WHERE email = ?', (email,))
            existing = cursor.fetchone()
            
            if existing:
                # 账号已存在，更新
                account_id = existing[0]
                logger.info(f"账号已存在，更新: {email} (ID: {account_id})")
                
                # 更新账号信息
                success = self.update_account(account_id, account_data)
                return account_id if success else None
            else:
                # 账号不存在，插入
                logger.info(f"账号不存在，插入新账号: {email}")
                return self.add_account(account_data)
                
        except Exception as e:
            logger.error(f"Upsert 账号失败: {e}")
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def get_all_accounts(self, 
                         filter_type: str = None,
                         filter_status: str = None,
                         filter_month: str = None,
                         sort_by: str = 'created_at',
                         ascending: bool = False) -> List[Dict[str, Any]]:
        """
        获取账号列表（支持筛选和排序）
        
        Args:
            filter_type: 账号类型筛选（free/pro/team等）
            filter_status: 状态筛选（active/expired）
            filter_month: 月份筛选（格式：2025-10）
            sort_by: 排序字段
            ascending: 是否升序
            
        Returns:
            List[Dict]: 账号列表
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建 SQL 查询
            sql = 'SELECT * FROM accounts WHERE 1=1'
            params = []
            
            # 类型筛选（支持模糊匹配，free 匹配 free 和 free_trial）
            if filter_type:
                filter_type_lower = filter_type.lower()
                # 如果是基础类型（free/pro/business等），匹配所有包含该类型的
                # 例如：free 匹配 free 和 free_trial，pro 匹配 pro 和 pro_trial
                sql += ' AND (membership_type = ? OR membership_type LIKE ?)'
                params.append(filter_type_lower)
                params.append(f"{filter_type_lower}_%")  # free_trial, pro_trial 等
            
            # 状态筛选
            if filter_status:
                if filter_status == 'expired':
                    # ⭐ "已失效"筛选：包含 status='expired' 或 is_invalid=1 的账号
                    sql += ' AND (status = ? OR is_invalid = 1)'
                    params.append(filter_status)
                elif filter_status == 'active':
                    # ⭐ "仅有效"筛选：status='active' 且 is_invalid=0 的账号（排除红×）
                    sql += ' AND status = ? AND (is_invalid = 0 OR is_invalid IS NULL)'
                    params.append(filter_status)
                elif filter_status == 'no_payment':
                    # ⭐ "未绑卡"筛选：FREE账号且无剩余天数且无订阅状态
                    # 条件：membership_type 为 free/free_trial 且 days_remaining = 0 (或NULL) 且 subscription_status 为空
                    sql += ' AND membership_type LIKE ? AND (days_remaining = 0 OR days_remaining IS NULL) AND (subscription_status IS NULL OR subscription_status = "")'
                    params.append('free%')
                else:
                    sql += ' AND status = ?'
                    params.append(filter_status)
            
            # 月份筛选
            if filter_month:
                sql += ' AND strftime("%Y-%m", created_at) = ?'
                params.append(filter_month)
            
            # 排序（处理NULL值）
            order = 'ASC' if ascending else 'DESC'
            
            # ⭐ 对于 total_cost 字段，NULL 值视为 0
            if sort_by == 'total_cost':
                sql += f' ORDER BY COALESCE({sort_by}, 0) {order}'
            else:
                sql += f' ORDER BY {sort_by} {order}'
            
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            
            # 转换为字典列表并解密
            accounts = []
            for row in rows:
                account = dict(row)
                
                # 解密敏感字段
                if account.get('password'):
                    try:
                        account['password'] = self.crypto.decrypt(account['password'])
                    except:
                        pass
                
                if account.get('access_token'):
                    try:
                        account['access_token'] = self.crypto.decrypt(account['access_token'])
                    except:
                        pass
                
                if account.get('refresh_token'):
                    try:
                        account['refresh_token'] = self.crypto.decrypt(account['refresh_token'])
                    except:
                        pass
                
                # ⭐ 解密 session_token
                if account.get('session_token'):
                    try:
                        account['session_token'] = self.crypto.decrypt(account['session_token'])
                    except:
                        pass
                
                # ⭐ 解密 machine_id_json
                if account.get('machine_id_json'):
                    try:
                        machine_info_json = self.crypto.decrypt(account['machine_id_json'])
                        account['machine_info'] = json.loads(machine_info_json)
                    except:
                        pass
                
                accounts.append(account)
            
            return accounts
            
        except Exception as e:
            logger.error(f"获取账号列表失败: {e}")
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def get_account_stats(self) -> Dict[str, Any]:
        """
        获取账号统计信息
        
        Returns:
            Dict: 统计信息
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 总数
            cursor.execute('SELECT COUNT(*) FROM accounts')
            total = cursor.fetchone()[0]
            
            # 按类型统计
            cursor.execute('SELECT membership_type, COUNT(*) FROM accounts GROUP BY membership_type')
            by_type = dict(cursor.fetchall())
            
            # 按状态统计
            cursor.execute('SELECT status, COUNT(*) FROM accounts GROUP BY status')
            by_status = dict(cursor.fetchall())
            
            # 平均使用率
            cursor.execute('SELECT AVG(usage_percent) FROM accounts WHERE status = "active"')
            avg_usage = cursor.fetchone()[0] or 0
            
            return {
                'total': total,
                'by_type': by_type,
                'by_status': by_status,
                'avg_usage': round(avg_usage, 1)
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'total': 0, 'by_type': {}, 'by_status': {}, 'avg_usage': 0}
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取账号
        
        Args:
            account_id: 账号 ID
            
        Returns:
            Optional[Dict]: 账号信息或 None
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
            row = cursor.fetchone()
            
            if row:
                account = dict(row)
                
                # 解密敏感字段
                if account.get('access_token'):
                    try:
                        account['access_token'] = self.crypto.decrypt(account['access_token'])
                    except:
                        pass
                
                if account.get('refresh_token'):
                    try:
                        account['refresh_token'] = self.crypto.decrypt(account['refresh_token'])
                    except:
                        pass
                
                # ⭐ 解密 session_token
                if account.get('session_token'):
                    try:
                        account['session_token'] = self.crypto.decrypt(account['session_token'])
                    except:
                        pass
                
                # ⭐ 解密 machine_id_json
                if account.get('machine_id_json'):
                    try:
                        machine_info_json = self.crypto.decrypt(account['machine_id_json'])
                        account['machine_info'] = json.loads(machine_info_json)
                    except:
                        pass
                
                return account
            
            return None
            
        except Exception as e:
            logger.error(f"获取账号失败: {e}")
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def update_account(self, account_id: int, data: Dict[str, Any]) -> bool:
        """
        更新账号信息
        
        Args:
            account_id: 账号 ID
            data: 要更新的数据
            
        Returns:
            bool: 是否成功
        """
        conn = None
        try:
            # 加密敏感字段
            encrypted_data = data.copy()
            if 'password' in encrypted_data and encrypted_data['password']:
                encrypted_data['password'] = self.crypto.encrypt(encrypted_data['password'])
            if 'access_token' in encrypted_data and encrypted_data['access_token']:
                encrypted_data['access_token'] = self.crypto.encrypt(encrypted_data['access_token'])
            if 'refresh_token' in encrypted_data and encrypted_data['refresh_token']:
                encrypted_data['refresh_token'] = self.crypto.encrypt(encrypted_data['refresh_token'])
            # ⭐ 加密 session_token
            if 'session_token' in encrypted_data and encrypted_data['session_token']:
                encrypted_data['session_token'] = self.crypto.encrypt(encrypted_data['session_token'])
            # ⭐ 加密 machine_info（机器码信息）- 转换为 machine_id_json
            if 'machine_info' in encrypted_data and encrypted_data['machine_info']:
                import json
                machine_info_json = json.dumps(encrypted_data['machine_info'])
                encrypted_data['machine_id_json'] = self.crypto.encrypt(machine_info_json)
                # 移除原始的 machine_info 字段，避免尝试更新不存在的列
                del encrypted_data['machine_info']
            
            # 字段名映射（处理 SQL 关键字和字段转换）
            field_mapping = {
                'limit': 'limit_value',  # limit 是 SQL 关键字
            }
            
            # 需要跳过的字段（不存在于数据库中）
            skip_fields = {'id', 'machine_info'}  # machine_info 已转换为 machine_id_json
            
            # 构建 UPDATE 语句
            fields = []
            values = []
            for key, value in encrypted_data.items():
                if key not in skip_fields:  # 跳过 ID 和不存在的字段
                    # 映射字段名
                    db_field = field_mapping.get(key, key)
                    fields.append(f"{db_field} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            values.append(account_id)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = f"UPDATE accounts SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, tuple(values))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"成功更新账号 ID: {account_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新账号失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def delete_account(self, account_id: int) -> bool:
        """
        删除账号
        
        Args:
            account_id: 账号 ID
            
        Returns:
            bool: 是否成功
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"成功删除账号 ID: {account_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def update_last_used(self, account_id: int):
        """
        更新账号最后使用时间
        
        Args:
            account_id: 账号 ID
        """
        self.update_account(account_id, {
            'last_used': datetime.now().isoformat()
        })
    
    def update_account_status(self, account_id: int, usage_info: Dict[str, Any]):
        """
        更新账号状态信息（完整版，和检测当前账号一样）
        
        Args:
            account_id: 账号 ID
            usage_info: 使用情况信息（从 API 获取的完整信息）
        """
        # ⭐ 将模型费用转为JSON字符串
        model_usage_json = None
        if 'model_usage' in usage_info and usage_info['model_usage']:
            import json
            try:
                model_usage_json = json.dumps(usage_info['model_usage'])
            except:
                pass
        
        update_data = {
            'email': usage_info.get('email'),  # ⭐ 更新邮箱
            'user_id': usage_info.get('user_id'),  # ⭐ 更新用户ID
            'membership_type': usage_info.get('membership_type', 'free'),
            'usage_percent': usage_info.get('usage_percent', 0.0),
            'used': usage_info.get('used', 0),
            'limit_value': usage_info.get('limit', 1000),
            'days_remaining': usage_info.get('days_remaining', 0),  # ⭐ 添加剩余天数
            'subscription_status': usage_info.get('subscription_status'),  # ⭐ 订阅状态
            'total_cost': usage_info.get('total_cost'),  # ⭐ 保存真实费用
            'total_tokens': usage_info.get('total_tokens'),  # ⭐ 保存总tokens
            'unpaid_amount': usage_info.get('unpaid_amount'),  # ⭐ 保存欠费金额
            'model_usage_json': model_usage_json,  # ⭐ 保存模型费用详情
            'last_used': usage_info.get('last_used'),  # ⭐ 保存最后使用时间（从API获取）
            'last_refresh_time': usage_info.get('last_refresh_time'),  # ⭐ 保存最后刷新时间（增量刷新）
            'accumulated_cost': usage_info.get('accumulated_cost'),  # ⭐ 保存累计金额（增量刷新）
            'last_refreshed': datetime.now().isoformat()
        }
        
        # 过滤掉 None 值
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        self.update_account(account_id, update_data)


# 全局存储实例
_storage = None


def get_storage(db_path: str = None) -> AccountStorage:
    """
    获取全局存储实例（单例）
    
    Args:
        db_path: 数据库路径（仅首次调用时使用）
        
    Returns:
        AccountStorage: 存储实例
    """
    global _storage
    if _storage is None:
        _storage = AccountStorage(db_path or "./data/accounts.db")
    return _storage


