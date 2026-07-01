import json
from datetime import datetime


class TaxEngine:
    """Indian Income Tax Calculator for FY 2025-26 (AY 2026-27)"""

    # New Regime Slabs (default for FY 2025-26)
    NEW_REGIME_SLABS = [
        (400000, 0.00),
        (800000, 0.05),
        (1200000, 0.10),
        (1600000, 0.15),
        (2000000, 0.20),
        (2400000, 0.25),
        (float('inf'), 0.30)
    ]

    # Old Regime Slabs (below 60)
    OLD_REGIME_SLABS_GENERAL = [
        (250000, 0.00),
        (500000, 0.05),
        (1000000, 0.20),
        (float('inf'), 0.30)
    ]

    # Old Regime Slabs (60-80 Senior Citizen)
    OLD_REGIME_SLABS_SENIOR = [
        (300000, 0.00),
        (500000, 0.05),
        (1000000, 0.20),
        (float('inf'), 0.30)
    ]

    # Old Regime Slabs (80+ Super Senior)
    OLD_REGIME_SLABS_SUPER_SENIOR = [
        (500000, 0.00),
        (1000000, 0.20),
        (float('inf'), 0.30)
    ]

    NEW_REGIME_STANDARD_DEDUCTION = 75000
    OLD_REGIME_STANDARD_DEDUCTION = 50000
    MAX_80C = 150000
    MAX_80CCD1B = 50000
    MAX_80D_SELF_GENERAL = 25000
    MAX_80D_SELF_SENIOR = 50000
    MAX_80D_PARENTS_GENERAL = 25000
    MAX_80D_PARENTS_SENIOR = 50000
    CESS_RATE = 0.04
    REBATE_87A_NEW_LIMIT = 1200000   # Taxable income limit for rebate
    REBATE_87A_NEW_MAX = 60000       # Max rebate amount
    REBATE_87A_OLD_LIMIT = 500000
    REBATE_87A_OLD_MAX = 12500

    def calculate_tax_on_slabs(self, taxable_income, slabs):
        """Calculate tax based on income slabs."""
        tax = 0
        prev_limit = 0
        for limit, rate in slabs:
            if taxable_income <= prev_limit:
                break
            taxable_in_slab = min(taxable_income, limit) - prev_limit
            tax += taxable_in_slab * rate
            prev_limit = limit
        return tax

    def calculate_hra_exemption(self, basic_salary, da, hra_received, rent_paid, is_metro):
        """Calculate HRA exemption (Old Regime only)."""
        if rent_paid <= 0 or hra_received <= 0:
            return 0
        salary = basic_salary + da
        metro_percent = 0.50 if is_metro else 0.40
        exemption = min(
            hra_received,
            rent_paid - (0.10 * salary),
            metro_percent * salary
        )
        return max(0, exemption)

    def calculate_old_regime_deductions(self, deductions_data):
        """Calculate total deductions under old regime."""
        total = 0
        breakdown = {}

        # Section 80C
        sec_80c = min(deductions_data.get('sec_80c', 0), self.MAX_80C)
        if sec_80c > 0:
            breakdown['Section 80C'] = sec_80c
            total += sec_80c

        # Section 80CCD(1B) - NPS
        sec_80ccd = min(deductions_data.get('nps', 0), self.MAX_80CCD1B)
        if sec_80ccd > 0:
            breakdown['Section 80CCD(1B) - NPS'] = sec_80ccd
            total += sec_80ccd

        # Section 80D - Health Insurance
        age_group = deductions_data.get('age_group', 'below_60')
        max_self = self.MAX_80D_SELF_SENIOR if age_group != 'below_60' else self.MAX_80D_SELF_GENERAL
        sec_80d_self = min(deductions_data.get('health_insurance_self', 0), max_self)

        parents_senior = deductions_data.get('parents_senior', False)
        max_parents = self.MAX_80D_PARENTS_SENIOR if parents_senior else self.MAX_80D_PARENTS_GENERAL
        sec_80d_parents = min(deductions_data.get('health_insurance_parents', 0), max_parents)

        sec_80d = sec_80d_self + sec_80d_parents
        if sec_80d > 0:
            breakdown['Section 80D - Health Insurance'] = sec_80d
            total += sec_80d

        # Section 80E - Education Loan (no limit)
        sec_80e = deductions_data.get('education_loan_interest', 0)
        if sec_80e > 0:
            breakdown['Section 80E - Education Loan'] = sec_80e
            total += sec_80e

        # Section 80G - Donations
        sec_80g = deductions_data.get('donations', 0)
        if sec_80g > 0:
            breakdown['Section 80G - Donations'] = sec_80g
            total += sec_80g

        # HRA
        hra = deductions_data.get('hra_exemption', 0)
        if hra > 0:
            breakdown['HRA Exemption'] = hra
            total += hra

        # Standard Deduction
        breakdown['Standard Deduction'] = self.OLD_REGIME_STANDARD_DEDUCTION
        total += self.OLD_REGIME_STANDARD_DEDUCTION

        return total, breakdown

    def calculate_surcharge(self, tax, taxable_income):
        """Calculate surcharge based on income level."""
        if taxable_income <= 5000000:
            return 0
        elif taxable_income <= 10000000:
            return tax * 0.10
        elif taxable_income <= 20000000:
            return tax * 0.15
        elif taxable_income <= 50000000:
            return tax * 0.25
        else:
            return tax * 0.37

    def calculate_new_regime(self, gross_income):
        """Calculate tax under New Regime."""
        standard_deduction = self.NEW_REGIME_STANDARD_DEDUCTION
        taxable_income = max(0, gross_income - standard_deduction)

        tax = self.calculate_tax_on_slabs(taxable_income, self.NEW_REGIME_SLABS)

        # Section 87A Rebate
        rebate = 0
        if taxable_income <= self.REBATE_87A_NEW_LIMIT:
            rebate = min(tax, self.REBATE_87A_NEW_MAX)
            tax -= rebate

        surcharge = self.calculate_surcharge(tax, taxable_income)
        cess = (tax + surcharge) * self.CESS_RATE
        total_tax = tax + surcharge + cess

        return {
            'regime': 'New Regime',
            'gross_income': gross_income,
            'standard_deduction': standard_deduction,
            'taxable_income': taxable_income,
            'tax_before_rebate': tax + rebate,
            'rebate_87a': rebate,
            'tax_after_rebate': tax,
            'surcharge': round(surcharge),
            'cess': round(cess),
            'total_tax': round(total_tax),
            'effective_rate': round((total_tax / gross_income) * 100, 2) if gross_income > 0 else 0,
            'deductions_breakdown': {'Standard Deduction': standard_deduction}
        }

    def calculate_old_regime(self, gross_income, deductions_data):
        """Calculate tax under Old Regime."""
        age_group = deductions_data.get('age_group', 'below_60')

        if age_group == 'above_80':
            slabs = self.OLD_REGIME_SLABS_SUPER_SENIOR
        elif age_group == '60_to_80':
            slabs = self.OLD_REGIME_SLABS_SENIOR
        else:
            slabs = self.OLD_REGIME_SLABS_GENERAL

        total_deductions, deductions_breakdown = self.calculate_old_regime_deductions(deductions_data)
        taxable_income = max(0, gross_income - total_deductions)

        tax = self.calculate_tax_on_slabs(taxable_income, slabs)

        # Section 87A Rebate
        rebate = 0
        if taxable_income <= self.REBATE_87A_OLD_LIMIT:
            rebate = min(tax, self.REBATE_87A_OLD_MAX)
            tax -= rebate

        surcharge = self.calculate_surcharge(tax, taxable_income)
        cess = (tax + surcharge) * self.CESS_RATE
        total_tax = tax + surcharge + cess

        return {
            'regime': 'Old Regime',
            'gross_income': gross_income,
            'total_deductions': total_deductions,
            'taxable_income': taxable_income,
            'tax_before_rebate': tax + rebate,
            'rebate_87a': rebate,
            'tax_after_rebate': tax,
            'surcharge': round(surcharge),
            'cess': round(cess),
            'total_tax': round(total_tax),
            'effective_rate': round((total_tax / gross_income) * 100, 2) if gross_income > 0 else 0,
            'deductions_breakdown': deductions_breakdown
        }

    def compare_regimes(self, gross_income, deductions_data):
        """Compare both regimes and recommend the better one."""
        new_regime = self.calculate_new_regime(gross_income)
        old_regime = self.calculate_old_regime(gross_income, deductions_data)

        savings = abs(new_regime['total_tax'] - old_regime['total_tax'])

        if new_regime['total_tax'] <= old_regime['total_tax']:
            recommended = 'New Regime'
            reason = f'New Regime saves you \u20b9{savings:,.0f} compared to Old Regime.'
        else:
            recommended = 'Old Regime'
            reason = f'Old Regime saves you \u20b9{savings:,.0f} compared to New Regime due to your deductions.'

        return {
            'new_regime': new_regime,
            'old_regime': old_regime,
            'recommended': recommended,
            'savings': savings,
            'reason': reason
        }

    def get_monthly_breakdown(self, annual_income, annual_tax):
        """Get monthly income and tax breakdown."""
        return {
            'monthly_gross': round(annual_income / 12),
            'monthly_tax': round(annual_tax / 12),
            'monthly_net': round((annual_income - annual_tax) / 12),
            'annual_gross': annual_income,
            'annual_tax': annual_tax,
            'annual_net': annual_income - annual_tax
        }

    def get_document_checklist(self, user_data):
        """Generate personalized document checklist based on user data."""
        checklist = [
            {'doc': 'PAN Card', 'required': True, 'reason': 'Mandatory for ITR filing'},
            {'doc': 'Aadhaar Card', 'required': True, 'reason': 'Must be linked with PAN'},
        ]

        if user_data.get('employment_type') == 'salaried':
            checklist.append({'doc': 'Form 16', 'required': True, 'reason': 'TDS certificate from employer'})

        checklist.append({'doc': 'Form 26AS / AIS', 'required': True, 'reason': 'Tax credit statement'})
        checklist.append({'doc': 'Bank Statements', 'required': True, 'reason': 'Interest income & transactions'})

        if user_data.get('has_investments', False):
            checklist.append({'doc': 'Investment Proofs (80C)', 'required': True, 'reason': 'PPF, ELSS, LIC receipts'})

        if user_data.get('health_insurance_self', 0) > 0:
            checklist.append({'doc': 'Health Insurance Premium Receipt', 'required': True, 'reason': 'Section 80D claim'})

        if user_data.get('rent_paid', 0) > 0:
            checklist.append({'doc': 'Rent Receipts', 'required': True, 'reason': 'HRA exemption claim'})
            checklist.append({'doc': 'Landlord PAN (if rent > \u20b91L/year)', 'required': True, 'reason': 'Required for HRA > \u20b91 lakh'})

        if user_data.get('education_loan_interest', 0) > 0:
            checklist.append({'doc': 'Education Loan Interest Certificate', 'required': True, 'reason': 'Section 80E claim'})

        if user_data.get('has_home_loan', False):
            checklist.append({'doc': 'Home Loan Interest Certificate', 'required': True, 'reason': 'Section 24(b) claim'})

        if user_data.get('donations', 0) > 0:
            checklist.append({'doc': 'Donation Receipts (80G)', 'required': True, 'reason': 'Section 80G claim'})

        if user_data.get('marital_status') == 'married' and user_data.get('children_count', 0) > 0:
            checklist.append({'doc': 'Children Tuition Fee Receipts', 'required': True, 'reason': 'Section 80C (tuition fees)'})

        return checklist
