"""Esquema inicial de Forja (contracts/domain.md §4), con extensiones e índices.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for extension in ("unaccent", "pg_trgm", "citext"):
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
    op.create_table('app_setting',
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_app_setting'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('actor_user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('target', sa.Text(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('ip_hash', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_table('equipment',
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('name_es', sa.Text(), nullable=False),
    sa.Column('name_en', sa.Text(), nullable=False),
    sa.Column('group', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('"group" IN (\'gym\', \'home_basic\', \'bodyweight\', \'cardio_machine\', \'other\')', name=op.f('ck_equipment_group')),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_equipment'))
    )
    op.create_table('food',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name_es', sa.Text(), nullable=False),
    sa.Column('category', sa.Text(), nullable=False),
    sa.Column('fdc_id', sa.Integer(), nullable=False),
    sa.Column('per_100g', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('diet_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('allergens', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('macro_role', sa.Text(), nullable=False),
    sa.Column('typical_portion_g', sa.Numeric(precision=6, scale=1), nullable=False),
    sa.Column('unit_grams', sa.Numeric(precision=6, scale=1), nullable=True),
    sa.Column('unit_name_es', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_food'))
    )
    op.create_index('ix_food_name_es_trgm', 'food', ['name_es'], unique=False, postgresql_using='gin', postgresql_ops={'name_es': 'gin_trgm_ops'})
    op.create_table('ingest_run',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('commit', sa.String(length=40), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('dry_run', sa.Boolean(), nullable=False),
    sa.Column('triggered_by', sa.UUID(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('checksums_sha256', sa.String(length=64), nullable=True),
    sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name=op.f('ck_ingest_run_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ingest_run'))
    )
    op.create_table('muscle',
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('name_es', sa.Text(), nullable=False),
    sa.Column('name_en', sa.Text(), nullable=False),
    sa.Column('region', sa.Text(), nullable=False),
    sa.Column('volume_group', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("region IN ('upper', 'lower', 'core', 'cardio', 'other')", name=op.f('ck_muscle_region')),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_muscle'))
    )
    op.create_table('user',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('locale', sa.Text(), nullable=False),
    sa.Column('units', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("locale IN ('es', 'en')", name=op.f('ck_user_locale')),
    sa.CheckConstraint("role IN ('user', 'admin')", name=op.f('ck_user_role')),
    sa.CheckConstraint("units IN ('metric', 'imperial')", name=op.f('ck_user_units')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user')),
    sa.UniqueConstraint('email', name=op.f('uq_user_email'))
    )
    op.create_table('body_metric',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('body_fat_pct', sa.Numeric(precision=4, scale=1), nullable=True),
    sa.Column('waist_cm', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_body_metric_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_body_metric')),
    sa.UniqueConstraint('user_id', 'date', name='user_date')
    )
    op.create_table('exercise',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('media_id', sa.Text(), nullable=False),
    sa.Column('name_en', sa.Text(), nullable=False),
    sa.Column('display_name_en', sa.Text(), nullable=False),
    sa.Column('name_es', sa.Text(), nullable=False),
    sa.Column('slug', sa.Text(), nullable=False),
    sa.Column('body_part', sa.Text(), nullable=False),
    sa.Column('equipment_code', sa.Text(), nullable=False),
    sa.Column('target_muscle', sa.Text(), nullable=False),
    sa.Column('primary_group_muscle', sa.Text(), nullable=False),
    sa.Column('movement_pattern', sa.Text(), nullable=False),
    sa.Column('mechanic', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('difficulty', sa.SmallInteger(), nullable=False),
    sa.Column('is_staple', sa.Boolean(), nullable=False),
    sa.Column('laterality', sa.Text(), nullable=False),
    sa.Column('demo_sex', sa.Text(), nullable=True),
    sa.Column('variant_group', sa.Text(), nullable=False),
    sa.Column('variant_kind', sa.Text(), nullable=True),
    sa.Column('variant_label_es', sa.Text(), nullable=True),
    sa.Column('load_type', sa.Text(), nullable=False),
    sa.Column('thumb_path', sa.Text(), nullable=False),
    sa.Column('gif_path', sa.Text(), nullable=False),
    sa.Column('media_sha256_thumb', sa.String(length=64), nullable=False),
    sa.Column('media_sha256_gif', sa.String(length=64), nullable=False),
    sa.Column('source_commit', sa.String(length=40), nullable=False),
    sa.Column('deprecated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('enrichment_version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("body_part IN ('upper_arms', 'upper_legs', 'back', 'waist', 'chest', 'shoulders', 'lower_legs', 'lower_arms', 'cardio', 'neck')", name=op.f('ck_exercise_body_part')),
    sa.CheckConstraint("demo_sex IS NULL OR demo_sex IN ('male', 'female')", name=op.f('ck_exercise_demo_sex')),
    sa.CheckConstraint("id ~ '^[0-9]{4}$'", name=op.f('ck_exercise_id_format')),
    sa.CheckConstraint("laterality IN ('bilateral', 'unilateral')", name=op.f('ck_exercise_laterality')),
    sa.CheckConstraint("load_type IN ('external', 'bodyweight', 'assisted', 'time')", name=op.f('ck_exercise_load_type')),
    sa.CheckConstraint("mechanic IN ('compound', 'isolation')", name=op.f('ck_exercise_mechanic')),
    sa.CheckConstraint("movement_pattern IN ('squat', 'lunge', 'hinge', 'horizontal_push', 'vertical_push', 'horizontal_pull', 'vertical_pull', 'elbow_flexion', 'elbow_extension', 'shoulder_raise', 'chest_fly', 'rear_delt', 'knee_extension', 'knee_flexion', 'hip_abduction', 'hip_adduction', 'glute_isolation', 'calf', 'core_flexion', 'core_anti_extension', 'core_rotation', 'core_lateral', 'shrug', 'forearm', 'neck', 'carry', 'plyometric', 'cardio', 'mobility', 'other')", name=op.f('ck_exercise_movement_pattern')),
    sa.CheckConstraint("role IN ('main', 'accessory', 'core', 'cardio', 'mobility', 'warmup')", name=op.f('ck_exercise_role')),
    sa.CheckConstraint("variant_kind IS NULL OR variant_kind IN ('version', 'demonstrator', 'camera_angle', 'duplicate')", name=op.f('ck_exercise_variant_kind')),
    sa.CheckConstraint('difficulty BETWEEN 1 AND 3', name=op.f('ck_exercise_difficulty')),
    sa.ForeignKeyConstraint(['equipment_code'], ['equipment.code'], name=op.f('fk_exercise_equipment_code_equipment')),
    sa.ForeignKeyConstraint(['primary_group_muscle'], ['muscle.code'], name=op.f('fk_exercise_primary_group_muscle_muscle')),
    sa.ForeignKeyConstraint(['target_muscle'], ['muscle.code'], name=op.f('fk_exercise_target_muscle_muscle')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exercise')),
    sa.UniqueConstraint('slug', name=op.f('uq_exercise_slug'))
    )
    op.create_index('ix_exercise_display_name_en_trgm', 'exercise', ['display_name_en'], unique=False, postgresql_using='gin', postgresql_ops={'display_name_en': 'gin_trgm_ops'})
    op.create_index('ix_exercise_equipment_code', 'exercise', ['equipment_code'], unique=False)
    op.create_index('ix_exercise_movement_pattern', 'exercise', ['movement_pattern'], unique=False)
    op.create_index('ix_exercise_name_es_trgm', 'exercise', ['name_es'], unique=False, postgresql_using='gin', postgresql_ops={'name_es': 'gin_trgm_ops'})
    op.create_index('ix_exercise_search_vector', 'exercise', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index('ix_exercise_target_muscle', 'exercise', ['target_muscle'], unique=False)
    op.create_index('ix_exercise_variant_group', 'exercise', ['variant_group'], unique=False)
    op.create_table('idempotency_key',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('status_code', sa.SmallInteger(), nullable=False),
    sa.Column('response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_idempotency_key_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'key', name=op.f('pk_idempotency_key'))
    )
    op.create_table('meal_plan',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('diet_type', sa.Text(), nullable=False),
    sa.Column('meals_per_day', sa.SmallInteger(), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('seed', sa.BigInteger(), nullable=False),
    sa.Column('nutrition_version', sa.Text(), nullable=False),
    sa.Column('foods_hash', sa.String(length=64), nullable=False),
    sa.Column('target', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('notices', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_meal_plan_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meal_plan'))
    )
    op.create_table('nutrition_settings',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('goal', sa.Text(), nullable=False),
    sa.Column('pace', sa.Text(), nullable=False),
    sa.Column('diet_type', sa.Text(), nullable=False),
    sa.Column('meals_per_day', sa.SmallInteger(), nullable=False),
    sa.Column('allergens', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('excluded_food_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('disliked_food_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('pregnant', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('breastfeeding', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_nutrition_settings_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_nutrition_settings'))
    )
    op.create_table('nutrition_target',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('kcal', sa.Numeric(precision=7, scale=1), nullable=True),
    sa.Column('protein_g', sa.Numeric(precision=7, scale=1), nullable=True),
    sa.Column('fat_g', sa.Numeric(precision=7, scale=1), nullable=True),
    sa.Column('carbs_g', sa.Numeric(precision=7, scale=1), nullable=True),
    sa.Column('fiber_g', sa.Numeric(precision=7, scale=1), nullable=True),
    sa.Column('method', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_nutrition_target_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_nutrition_target'))
    )
    op.create_table('profile',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('sex', sa.Text(), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('height_cm', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('experience', sa.Text(), nullable=False),
    sa.Column('activity_level', sa.Text(), nullable=False),
    sa.Column('equipment_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('limitations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('parq_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parq_flagged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('parq_completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('diet_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("activity_level IN ('sedentary', 'light', 'moderate', 'high')", name=op.f('ck_profile_activity_level')),
    sa.CheckConstraint("experience IN ('beginner', 'intermediate', 'advanced')", name=op.f('ck_profile_experience')),
    sa.CheckConstraint("sex IN ('male', 'female', 'unspecified')", name=op.f('ck_profile_sex')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_profile_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_profile'))
    )
    op.create_table('program',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('generator_input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('generator_version', sa.Text(), nullable=True),
    sa.Column('tables_hash', sa.String(length=64), nullable=True),
    sa.Column('seed', sa.BigInteger(), nullable=True),
    sa.Column('goal', sa.Text(), nullable=True),
    sa.Column('days_per_week', sa.SmallInteger(), nullable=False),
    sa.Column('weeks', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('weekly_volume', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('rationale_es', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source IN ('generated', 'manual', 'imported')", name=op.f('ck_program_source')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_program_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program'))
    )
    op.create_index('uq_program_user_id_active', 'program', ['user_id'], unique=True, postgresql_where=sa.text('is_active'))
    op.create_table('session',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_agent', sa.String(length=256), nullable=True),
    sa.Column('ip_hash', sa.String(length=64), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_session_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_session')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_session_token_hash'))
    )
    op.create_index('ix_session_user_id_revoked_at', 'session', ['user_id', 'revoked_at'], unique=False)
    op.create_table('exercise_alternative',
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('alt_id', sa.Text(), nullable=False),
    sa.Column('score', sa.Numeric(precision=4, scale=3), nullable=False),
    sa.Column('rank', sa.SmallInteger(), nullable=False),
    sa.CheckConstraint('rank BETWEEN 1 AND 8', name=op.f('ck_exercise_alternative_rank')),
    sa.ForeignKeyConstraint(['alt_id'], ['exercise.id'], name=op.f('fk_exercise_alternative_alt_id_exercise'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_exercise_alternative_exercise_id_exercise'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('exercise_id', 'alt_id', name=op.f('pk_exercise_alternative'))
    )
    op.create_table('exercise_instruction',
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('lang', sa.Text(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("lang IN ('en', 'es', 'it', 'tr', 'ru', 'zh', 'hi', 'pl', 'ko', 'fr')", name=op.f('ck_exercise_instruction_lang')),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_exercise_instruction_exercise_id_exercise'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('exercise_id', 'lang', name=op.f('pk_exercise_instruction'))
    )
    op.create_table('exercise_secondary_muscle',
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('muscle_code', sa.Text(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_exercise_secondary_muscle_exercise_id_exercise'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['muscle_code'], ['muscle.code'], name=op.f('fk_exercise_secondary_muscle_muscle_code_muscle')),
    sa.PrimaryKeyConstraint('exercise_id', 'muscle_code', name=op.f('pk_exercise_secondary_muscle'))
    )
    op.create_table('favorite_exercise',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_favorite_exercise_exercise_id_exercise')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_favorite_exercise_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'exercise_id', name=op.f('pk_favorite_exercise'))
    )
    op.create_table('meal_plan_item',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('day', sa.SmallInteger(), nullable=False),
    sa.Column('meal', sa.Text(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('food_id', sa.Text(), nullable=False),
    sa.Column('grams', sa.Numeric(precision=6, scale=1), nullable=False),
    sa.Column('units', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['food_id'], ['food.id'], name=op.f('fk_meal_plan_item_food_id_food')),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plan.id'], name=op.f('fk_meal_plan_item_plan_id_meal_plan'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meal_plan_item'))
    )
    op.create_table('program_week',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('program_id', sa.UUID(), nullable=False),
    sa.Column('index', sa.SmallInteger(), nullable=False),
    sa.Column('phase', sa.Text(), nullable=False),
    sa.Column('target_rir', sa.SmallInteger(), nullable=False),
    sa.Column('volume_ratio', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("phase IN ('accumulation', 'intensification', 'deload')", name=op.f('ck_program_week_phase')),
    sa.ForeignKeyConstraint(['program_id'], ['program.id'], name=op.f('fk_program_week_program_id_program'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_week')),
    sa.UniqueConstraint('program_id', 'index', name='program_index')
    )
    op.create_table('program_day',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('week_id', sa.UUID(), nullable=False),
    sa.Column('index', sa.SmallInteger(), nullable=False),
    sa.Column('template', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('focus', sa.Text(), nullable=True),
    sa.Column('weekday', sa.Text(), nullable=True),
    sa.Column('is_recovery', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('estimated_minutes', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['week_id'], ['program_week.id'], name=op.f('fk_program_day_week_id_program_week'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_day')),
    sa.UniqueConstraint('week_id', 'index', name='week_index')
    )
    op.create_table('program_block',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('day_id', sa.UUID(), nullable=False),
    sa.Column('order', sa.SmallInteger(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('rounds', sa.SmallInteger(), nullable=False),
    sa.Column('rest_between_rounds_s', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('warmup', 'main', 'superset', 'circuit', 'finisher', 'cooldown')", name=op.f('ck_program_block_kind')),
    sa.ForeignKeyConstraint(['day_id'], ['program_day.id'], name=op.f('fk_program_block_day_id_program_day'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_block'))
    )
    op.create_table('workout_session',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('client_uuid', sa.UUID(), nullable=False),
    sa.Column('program_id', sa.UUID(), nullable=True),
    sa.Column('program_day_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('perceived_effort', sa.SmallInteger(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('client_updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('in_progress', 'completed', 'abandoned')", name=op.f('ck_workout_session_status')),
    sa.CheckConstraint('perceived_effort BETWEEN 1 AND 10', name=op.f('ck_workout_session_perceived_effort')),
    sa.ForeignKeyConstraint(['program_day_id'], ['program_day.id'], name=op.f('fk_workout_session_program_day_id_program_day'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['program_id'], ['program.id'], name=op.f('fk_workout_session_program_id_program'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_workout_session_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workout_session')),
    sa.UniqueConstraint('user_id', 'client_uuid', name='user_client_uuid')
    )
    op.create_index('ix_workout_session_user_id_started_at', 'workout_session', ['user_id', sa.literal_column('started_at DESC')], unique=False)
    op.create_table('program_exercise',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('block_id', sa.UUID(), nullable=False),
    sa.Column('order', sa.SmallInteger(), nullable=False),
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('slot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('sets', sa.SmallInteger(), nullable=False),
    sa.Column('rep_min', sa.SmallInteger(), nullable=True),
    sa.Column('rep_max', sa.SmallInteger(), nullable=True),
    sa.Column('target_rir', sa.SmallInteger(), nullable=True),
    sa.Column('tempo', sa.Text(), nullable=True),
    sa.Column('rest_s', sa.SmallInteger(), nullable=False),
    sa.Column('duration_s', sa.Integer(), nullable=True),
    sa.Column('per_side', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('load_hint', sa.Text(), nullable=True),
    sa.Column('notes_es', sa.Text(), nullable=True),
    sa.Column('alternatives', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(rep_min IS NOT NULL AND rep_max IS NOT NULL) OR duration_s IS NOT NULL', name=op.f('ck_program_exercise_reps_or_duration')),
    sa.CheckConstraint('rep_min <= rep_max', name=op.f('ck_program_exercise_rep_range')),
    sa.ForeignKeyConstraint(['block_id'], ['program_block.id'], name=op.f('fk_program_exercise_block_id_program_block'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_program_exercise_exercise_id_exercise')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_exercise'))
    )
    op.create_table('set_log',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('program_exercise_id', sa.UUID(), nullable=True),
    sa.Column('set_index', sa.SmallInteger(), nullable=False),
    sa.Column('weight_kg', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('reps', sa.SmallInteger(), nullable=True),
    sa.Column('rir', sa.SmallInteger(), nullable=True),
    sa.Column('duration_s', sa.Integer(), nullable=True),
    sa.Column('is_warmup', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('client_uuid', sa.UUID(), nullable=False),
    sa.Column('client_updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_set_log_exercise_id_exercise')),
    sa.ForeignKeyConstraint(['program_exercise_id'], ['program_exercise.id'], name=op.f('fk_set_log_program_exercise_id_program_exercise'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['workout_session.id'], name=op.f('fk_set_log_session_id_workout_session'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_set_log')),
    sa.UniqueConstraint('client_uuid', name='client_uuid')
    )
    op.create_index('ix_set_log_session_id_exercise_id', 'set_log', ['session_id', 'exercise_id'], unique=False)
    op.create_table('personal_record',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('value', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('weight_kg', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('reps', sa.SmallInteger(), nullable=True),
    sa.Column('achieved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('set_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('e1rm', 'heaviest_set', 'volume')", name=op.f('ck_personal_record_kind')),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('fk_personal_record_exercise_id_exercise')),
    sa.ForeignKeyConstraint(['session_id'], ['workout_session.id'], name=op.f('fk_personal_record_session_id_workout_session'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['set_id'], ['set_log.id'], name=op.f('fk_personal_record_set_id_set_log'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_personal_record_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_personal_record')),
    sa.UniqueConstraint('user_id', 'exercise_id', 'kind', name='user_exercise_kind')
    )


def downgrade() -> None:
    # Las extensiones son de la instancia (pueden usarlas otras bases): no se eliminan.
    op.drop_table('personal_record')
    op.drop_index('ix_set_log_session_id_exercise_id', table_name='set_log')
    op.drop_table('set_log')
    op.drop_table('program_exercise')
    op.drop_index('ix_workout_session_user_id_started_at', table_name='workout_session')
    op.drop_table('workout_session')
    op.drop_table('program_block')
    op.drop_table('program_day')
    op.drop_table('program_week')
    op.drop_table('meal_plan_item')
    op.drop_table('favorite_exercise')
    op.drop_table('exercise_secondary_muscle')
    op.drop_table('exercise_instruction')
    op.drop_table('exercise_alternative')
    op.drop_index('ix_session_user_id_revoked_at', table_name='session')
    op.drop_table('session')
    op.drop_index('uq_program_user_id_active', table_name='program', postgresql_where=sa.text('is_active'))
    op.drop_table('program')
    op.drop_table('profile')
    op.drop_table('nutrition_target')
    op.drop_table('nutrition_settings')
    op.drop_table('meal_plan')
    op.drop_table('idempotency_key')
    op.drop_index('ix_exercise_variant_group', table_name='exercise')
    op.drop_index('ix_exercise_target_muscle', table_name='exercise')
    op.drop_index('ix_exercise_search_vector', table_name='exercise', postgresql_using='gin')
    op.drop_index('ix_exercise_name_es_trgm', table_name='exercise', postgresql_using='gin', postgresql_ops={'name_es': 'gin_trgm_ops'})
    op.drop_index('ix_exercise_movement_pattern', table_name='exercise')
    op.drop_index('ix_exercise_equipment_code', table_name='exercise')
    op.drop_index('ix_exercise_display_name_en_trgm', table_name='exercise', postgresql_using='gin', postgresql_ops={'display_name_en': 'gin_trgm_ops'})
    op.drop_table('exercise')
    op.drop_table('body_metric')
    op.drop_table('user')
    op.drop_table('muscle')
    op.drop_table('ingest_run')
    op.drop_index('ix_food_name_es_trgm', table_name='food', postgresql_using='gin', postgresql_ops={'name_es': 'gin_trgm_ops'})
    op.drop_table('food')
    op.drop_table('equipment')
    op.drop_table('audit_log')
    op.drop_table('app_setting')
