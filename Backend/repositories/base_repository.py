# Backend/repositories/base_repository.py
from database import get_connection, get_cursor
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """Repositorio base con operaciones CRUD genéricas"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    def get_all(self, limit: Optional[int] = None, **filters) -> List[Dict]:
        """Obtiene todos los registros con filtros opcionales"""
        try:
            conn, cur = get_cursor()
            query = f"SELECT * FROM {self.table_name}"
            params = []
            
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    where_clauses.append(f"{key} = %s")
                    params.append(value)
                query += " WHERE " + " AND ".join(where_clauses)
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error en get_all: {e}")
            return []
    
    def get_by_id(self, id: int) -> Optional[Dict]:
        """Obtiene un registro por su ID"""
        try:
            conn, cur = get_cursor()
            cur.execute(f"SELECT * FROM {self.table_name} WHERE id = %s", (id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error en get_by_id: {e}")
            return None
    
    def create(self, data: Dict) -> Optional[int]:
        """Crea un nuevo registro y retorna el ID"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = list(data.values())
            
            cur.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING id",
                values
            )
            id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return id
        except Exception as e:
            logger.error(f"Error en create: {e}")
            return None
    
    def update(self, id: int, data: Dict) -> bool:
        """Actualiza un registro existente"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
            values = list(data.values()) + [id]
            
            cur.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = %s",
                values
            )
            affected = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            return affected > 0
        except Exception as e:
            logger.error(f"Error en update: {e}")
            return False
    
    def delete(self, id: int) -> bool:
        """Elimina un registro"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {self.table_name} WHERE id = %s", (id,))
            affected = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            return affected > 0
        except Exception as e:
            logger.error(f"Error en delete: {e}")
            return False
