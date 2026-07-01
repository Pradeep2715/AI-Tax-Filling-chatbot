import re
import json
from tax_engine import TaxEngine


class ChatBot:
    """Conversational AI chatbot for Indian Income Tax filing assistance."""

    STATES = [
        'GREETING', 'ASK_MARITAL', 'ASK_EMPLOYMENT', 'ASK_INCOME',
        'LIFESTYLE_HOUSING', 'LIFESTYLE_EXPENSES', 'LIFESTYLE_SAVINGS',
        'LIFESTYLE_INSURANCE', 'LIFESTYLE_EDUCATION', 'LIFESTYLE_OTHER',
        'CALCULATE', 'SUMMARY', 'FAQ', 'COMPLETE'
    ]

    FAQ_ANSWERS = {
        'itr_form': (
            "📋 **Which ITR Form to Use?**\n\n"
            "• **ITR-1 (Sahaj):** Salaried individuals with income up to ₹50 lakh, "
            "one house property, interest income.\n"
            "• **ITR-2:** Individuals with capital gains, foreign income, or multiple properties.\n"
            "• **ITR-3:** Individuals with business or professional income.\n"
            "• **ITR-4 (Sugam):** Presumptive income under Sec 44AD/44ADA.\n\n"
            "💡 Most salaried employees use **ITR-1**."
        ),
        'deadline': (
            "📅 **ITR Filing Deadlines for AY 2026-27:**\n\n"
            "• **Salaried / Non-audit:** 31st July 2026\n"
            "• **Audit cases:** 31st October 2026\n"
            "• **Revised return:** 31st December 2026\n"
            "• **Belated return:** 31st December 2026 (with penalty)\n\n"
            "⚠️ Late filing attracts a penalty of ₹1,000 to ₹5,000 under Section 234F."
        ),
        'penalty': (
            "⚠️ **Late Filing Penalties:**\n\n"
            "• Income up to ₹5 lakh: ₹1,000\n"
            "• Income above ₹5 lakh: ₹5,000\n"
            "• Interest under 234A: 1% per month on unpaid tax\n"
            "• Interest under 234B: 1% per month (advance tax shortfall)\n"
            "• Interest under 234C: 1% per month (deferred advance tax)\n\n"
            "💡 File on time to avoid penalties and interest!"
        ),
        'refund': (
            "💰 **Tax Refund Process:**\n\n"
            "• Refund is issued when taxes paid (TDS/advance tax) exceed actual liability.\n"
            "• After filing, verify your ITR via Aadhaar OTP or net banking.\n"
            "• Refunds are processed within 20-45 days of e-verification.\n"
            "• Refund is credited directly to your bank account linked with PAN.\n"
            "• Track refund status at: incometax.gov.in → 'Refund Status'\n\n"
            "💡 Ensure your bank account is pre-validated on the portal."
        ),
        'form16': (
            "📄 **Form 16:**\n\n"
            "• Issued by your employer as a TDS certificate.\n"
            "• **Part A:** TDS deducted and deposited details.\n"
            "• **Part B:** Salary breakup, deductions claimed, and tax computation.\n"
            "• Usually available by June 15th each year.\n"
            "• Download from your employer's HR portal or request from Accounts.\n\n"
            "💡 Form 16 is your primary document for ITR-1 filing."
        ),
        '26as': (
            "📊 **Form 26AS / AIS (Annual Information Statement):**\n\n"
            "• Form 26AS: Shows all TDS/TCS credited against your PAN.\n"
            "• AIS: Comprehensive view — salary, interest, dividends, property, mutual funds.\n"
            "• Access via incometax.gov.in → 'e-File' → 'Income Tax Returns' → 'View Form 26AS/AIS'\n"
            "• Cross-verify AIS data before filing — report discrepancies via TIS.\n\n"
            "💡 Always check 26AS before filing to ensure TDS credits match."
        )
    }

    def __init__(self):
        self.tax_engine = TaxEngine()

    @staticmethod
    def get_initial_state():
        """Return a fresh session state dictionary."""
        return {
            'state': 'ASK_MARITAL',
            'user_data': {
                'age_group': 'below_60'
            },
            'messages': [],
            'sub_state': None
        }

    def process_message(self, message, session_state):
        """Process a user message and return a response based on the current state.

        Args:
            message: The user's text input.
            session_state: Dict with keys 'state', 'user_data', 'messages', 'sub_state'.

        Returns:
            Dict with 'response', 'suggestions', 'type', 'data'.
        """
        msg = message.strip()
        msg_lower = msg.lower()
        state = session_state.get('state', 'ASK_MARITAL')
        user_data = session_state.get('user_data', {})
        sub_state = session_state.get('sub_state')

        # --- Global intent handlers (work in any state) ---

        # Reset
        if msg_lower in ('reset', 'start over', 'restart'):
            fresh = self.get_initial_state()
            session_state.update(fresh)
            return self._get_greeting_response()

        # Help
        if msg_lower == 'help':
            return {
                'response': (
                    "🆘 **Available Commands:**\n\n"
                    "• Type your answers naturally to move through the tax filing flow.\n"
                    "• **reset** — Start a new session from the beginning.\n"
                    "• **help** — Show this help message.\n"
                    "• Ask any tax FAQ at any time, e.g.:\n"
                    "  – \"Which ITR form should I use?\"\n"
                    "  – \"What is the deadline?\"\n"
                    "  – \"Tell me about Form 16\"\n"
                    "  – \"How do refunds work?\"\n"
                    "  – \"What are the penalties?\"\n"
                    "  – \"What is 26AS?\"\n\n"
                    "I'll answer your question and then continue right where we left off! 😊"
                ),
                'suggestions': ['Continue', 'Reset'],
                'type': 'text',
                'data': None
            }

        # FAQ detection at any state
        faq_response = self._check_faq(msg_lower)
        if faq_response and state not in ('GREETING',):
            faq_response['response'] += "\n\n---\n_Let's continue where we left off!_"
            return faq_response

        # --- State machine ---

        if state == 'GREETING':
            return self._handle_greeting(session_state)

        elif state == 'ASK_MARITAL':
            return self._handle_marital(msg_lower, session_state)

        elif state == 'ASK_EMPLOYMENT':
            return self._handle_employment(msg_lower, session_state)

        elif state == 'ASK_INCOME':
            return self._handle_income(msg, session_state)

        elif state == 'LIFESTYLE_HOUSING':
            return self._handle_housing(msg, msg_lower, session_state)

        elif state == 'LIFESTYLE_EXPENSES':
            return self._handle_expenses(msg, msg_lower, session_state)

        elif state == 'LIFESTYLE_SAVINGS':
            return self._handle_savings(msg, msg_lower, session_state)

        elif state == 'LIFESTYLE_INSURANCE':
            return self._handle_insurance(msg, msg_lower, session_state)

        elif state == 'LIFESTYLE_EDUCATION':
            return self._handle_education(msg, msg_lower, session_state)

        elif state == 'LIFESTYLE_OTHER':
            return self._handle_other(msg, msg_lower, session_state)

        elif state == 'CALCULATE':
            return self._handle_calculate(session_state)

        elif state == 'SUMMARY':
            return self._handle_summary(msg_lower, session_state)

        elif state == 'COMPLETE':
            return self._handle_complete(msg_lower, session_state)

        # Fallback
        return {
            'response': "I didn't quite understand that. Could you please rephrase? Type **help** for guidance.",
            'suggestions': ['Help', 'Reset'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Greeting
    # ------------------------------------------------------------------

    def _get_greeting_response(self):
        """Return the initial welcome message."""
        return {
            'response': (
                "🤖 **Welcome to TaxBot — Your AI Tax Filing Assistant!**\n\n"
                "I'll help you calculate your income tax for **FY 2025-26 (AY 2026-27)** "
                "and recommend the best tax regime for you.\n\n"
                "I'll ask you a few questions about your income, lifestyle, and investments "
                "to give you a personalized tax computation.\n\n"
                "Let's get started! 🚀\n\n"
                "**Are you Single or Married?**"
            ),
            'suggestions': ['Single', 'Married'],
            'type': 'options',
            'data': None
        }

    def _handle_greeting(self, session_state):
        """Transition from GREETING to ASK_MARITAL."""
        session_state['state'] = 'ASK_MARITAL'
        return self._get_greeting_response()

    # ------------------------------------------------------------------
    # Marital Status
    # ------------------------------------------------------------------

    def _handle_marital(self, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state')

        # Sub-state: ask children count for married users
        if sub_state == 'ask_children':
            num = self._parse_number(msg_lower)
            user_data['children_count'] = int(num) if num is not None else 0
            session_state['sub_state'] = None
            session_state['state'] = 'ASK_EMPLOYMENT'
            return {
                'response': (
                    f"👶 Children: **{user_data['children_count']}**. Noted!\n\n"
                    "💼 What is your **employment type**?"
                ),
                'suggestions': ['Salaried', 'Self-Employed', 'Freelancer'],
                'type': 'options',
                'data': None
            }

        if 'married' in msg_lower:
            user_data['marital_status'] = 'married'
            label = 'Married'
            session_state['sub_state'] = 'ask_children'
            return {
                'response': (
                    f"👍 Got it — **{label}**.\n\n"
                    "👨‍👩‍👧 How many children do you have? (Enter a number, or 0 if none)"
                ),
                'suggestions': ['0', '1', '2', '3'],
                'type': 'options',
                'data': None
            }
        elif 'single' in msg_lower or 'unmarried' in msg_lower:
            user_data['marital_status'] = 'single'
            user_data['children_count'] = 0
            label = 'Single'
            session_state['state'] = 'ASK_EMPLOYMENT'
            return {
                'response': (
                    f"👍 Got it — **{label}**.\n\n"
                    "💼 What is your **employment type**?"
                ),
                'suggestions': ['Salaried', 'Self-Employed', 'Freelancer'],
                'type': 'options',
                'data': None
            }
        else:
            return {
                'response': "Please select **Single** or **Married** to continue.",
                'suggestions': ['Single', 'Married'],
                'type': 'options',
                'data': None
            }

    # ------------------------------------------------------------------
    # Employment Type
    # ------------------------------------------------------------------

    def _handle_employment(self, msg_lower, session_state):
        user_data = session_state['user_data']

        if 'salaried' in msg_lower or 'salary' in msg_lower:
            user_data['employment_type'] = 'salaried'
            label = 'Salaried'
        elif 'self' in msg_lower or 'business' in msg_lower:
            user_data['employment_type'] = 'self_employed'
            label = 'Self-Employed'
        elif 'freelan' in msg_lower or 'contract' in msg_lower or 'gig' in msg_lower:
            user_data['employment_type'] = 'freelancer'
            label = 'Freelancer'
        else:
            return {
                'response': "Please choose: **Salaried**, **Self-Employed**, or **Freelancer**.",
                'suggestions': ['Salaried', 'Self-Employed', 'Freelancer'],
                'type': 'options',
                'data': None
            }

        session_state['state'] = 'ASK_INCOME'
        return {
            'response': (
                f"💼 Employment: **{label}**.\n\n"
                "💰 What is your **salary range**?"
            ),
            'suggestions': ['Below ₹8 Lakhs', 'Above ₹8 Lakhs', 'Custom'],
            'type': 'options',
            'data': None
        }

    def _proceed_after_income(self, income, session_state):
        user_data = session_state['user_data']
        # If salaried, calculate basic salary automatically as 50% of gross income
        if user_data.get('employment_type') == 'salaried':
            user_data['basic_salary'] = income * 0.50
            user_data['da'] = 0

        session_state['state'] = 'LIFESTYLE_HOUSING'
        session_state['sub_state'] = 'ask_own_or_rent'
        return {
            'response': (
                f"💰 Salary set to: **₹{income:,.0f}**\n\n"
                "🏠 Let's talk about your **housing situation**.\n\n"
                "Do you **own** a home or **rent**?"
            ),
            'suggestions': ['Own', 'Rent'],
            'type': 'options',
            'data': None
        }

    # ------------------------------------------------------------------
    # Income
    # ------------------------------------------------------------------

    def _handle_income(self, msg, session_state):
        user_data = session_state['user_data']
        msg_lower = msg.lower()
        sub_state = session_state.get('sub_state')

        # Sub-state: Custom income input
        if sub_state == 'ask_custom_income':
            income = self._parse_number(msg)
            if income is None or income <= 0:
                return {
                    'response': (
                        "❌ I couldn't parse that amount. Please enter a valid annual salary.\n\n"
                        "Examples: **12 lakh**, **1200000**, **12,00,000**, **12L**, **50k**"
                    ),
                    'suggestions': ['6 Lakhs', '12 Lakhs', '18 Lakhs'],
                    'type': 'text',
                    'data': None
                }
            user_data['gross_income'] = income
            session_state['sub_state'] = None
            return self._proceed_after_income(income, session_state)

        # Handle the options
        if 'below' in msg_lower or '8 lakh' in msg_lower and ('below' in msg_lower or '<' in msg_lower):
            income = 600000  # Default representative below 8L
            user_data['gross_income'] = income
            return self._proceed_after_income(income, session_state)
        elif 'above' in msg_lower or '8 lakh' in msg_lower and ('above' in msg_lower or '>' in msg_lower):
            income = 1500000  # Default representative above 8L
            user_data['gross_income'] = income
            return self._proceed_after_income(income, session_state)
        elif 'custom' in msg_lower:
            session_state['sub_state'] = 'ask_custom_income'
            return {
                'response': "✍️ Please enter your **annual gross income**:",
                'suggestions': ['6 Lakhs', '12 Lakhs', '18 Lakhs'],
                'type': 'text',
                'data': None
            }
        else:
            # Fallback parsing
            income = self._parse_number(msg)
            if income is not None and income > 0:
                user_data['gross_income'] = income
                return self._proceed_after_income(income, session_state)
            
            return {
                'response': "Please select your salary range, or choose **Custom** to type it.",
                'suggestions': ['Below ₹8 Lakhs', 'Above ₹8 Lakhs', 'Custom'],
                'type': 'options',
                'data': None
            }

    # ------------------------------------------------------------------
    # Housing
    # ------------------------------------------------------------------

    def _handle_housing(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_own_or_rent')

        # Sub-state: own or rent
        if sub_state == 'ask_own_or_rent':
            if 'rent' in msg_lower:
                user_data['housing'] = 'rent'
                session_state['sub_state'] = 'ask_monthly_rent'
                return {
                    'response': (
                        "🏠 You're renting. How much is your **monthly rent**?\n\n"
                        "_Type the amount, e.g., 15000 or 15k or 20000_"
                    ),
                    'suggestions': ['10000', '15000', '20000', '25000', '30000'],
                    'type': 'text',
                    'data': None
                }
            elif 'own' in msg_lower or 'bought' in msg_lower or 'house' in msg_lower:
                user_data['housing'] = 'own'
                user_data['rent_paid'] = 0
                session_state['sub_state'] = 'ask_home_loan'
                return {
                    'response': (
                        "🏡 You own a home.\n\n"
                        "Do you have a **home loan**?"
                    ),
                    'suggestions': ['Yes', 'No'],
                    'type': 'options',
                    'data': None
                }
            else:
                return {
                    'response': "Please select **Own** or **Rent**.",
                    'suggestions': ['Own', 'Rent'],
                    'type': 'options',
                    'data': None
                }

        # Sub-state: monthly rent
        if sub_state == 'ask_monthly_rent':
            rent = self._parse_number(msg)
            if rent is None or rent <= 0:
                return {
                    'response': "Please enter a valid monthly rent amount.",
                    'suggestions': ['10000', '15000', '20000', '25000'],
                    'type': 'text',
                    'data': None
                }
            user_data['monthly_rent'] = rent
            user_data['rent_paid'] = rent * 12
            session_state['sub_state'] = 'ask_metro'
            return {
                'response': (
                    f"🏠 Monthly Rent: **₹{rent:,.0f}** (₹{rent * 12:,.0f}/year)\n\n"
                    "🌆 Is your city a **metro city**?\n"
                    "(Delhi, Mumbai, Kolkata, or Chennai)"
                ),
                'suggestions': ['Yes', 'No'],
                'type': 'options',
                'data': None
            }

        # Sub-state: metro city
        if sub_state == 'ask_metro':
            user_data['is_metro'] = msg_lower in ('yes', 'y', 'yeah', 'yep', 'metro')
            session_state['sub_state'] = 'ask_hra'
            return {
                'response': (
                    f"🌆 Metro city: **{'Yes' if user_data['is_metro'] else 'No'}**\n\n"
                    "💼 How much **HRA (House Rent Allowance)** do you receive from your employer per month?\n"
                    "(If unsure or not applicable, type **0**)"
                ),
                'suggestions': ['0', '5000', '10000', '15000'],
                'type': 'text',
                'data': None
            }

        # Sub-state: HRA received
        if sub_state == 'ask_hra':
            hra = self._parse_number(msg)
            if hra is None:
                hra = 0
            user_data['hra_received'] = hra * 12  # annual
            user_data['monthly_hra'] = hra

            # Calculate HRA exemption
            if user_data.get('employment_type') == 'salaried' and hra > 0:
                basic = user_data.get('basic_salary', 0)
                da = user_data.get('da', 0)
                exemption = self.tax_engine.calculate_hra_exemption(
                    basic, da, user_data['hra_received'],
                    user_data['rent_paid'], user_data.get('is_metro', False)
                )
                user_data['hra_exemption'] = exemption
            else:
                user_data['hra_exemption'] = 0

            # Move to expenses
            session_state['state'] = 'LIFESTYLE_EXPENSES'
            session_state['sub_state'] = 'ask_monthly_expenses'
            marital = user_data.get('marital_status', 'single')
            prompt = (
                "🏠 Housing details recorded!\n\n" +
                (f"   HRA Exemption eligible: **₹{user_data['hra_exemption']:,.0f}**/year\n\n" if user_data['hra_exemption'] > 0 else "") +
                "💸 Now let's understand your **monthly expenses**.\n\n"
            )
            if marital == 'married':
                prompt += "What are your approximate **total household monthly expenses**?\n(Include food, utilities, transport, children expenses, etc.)"
            else:
                prompt += "What are your approximate **monthly living expenses**?\n(Include food, utilities, transport, etc.)"
            return {
                'response': prompt,
                'suggestions': ['20000', '30000', '40000', '50000'],
                'type': 'text',
                'data': None
            }

        # Sub-state: home loan
        if sub_state == 'ask_home_loan':
            if msg_lower in ('yes', 'y', 'yeah', 'yep'):
                user_data['has_home_loan'] = True
                session_state['sub_state'] = 'ask_home_loan_interest'
                return {
                    'response': (
                        "🏡 How much is your **annual home loan interest**?\n"
                        "(Section 24(b) allows deduction up to ₹2 lakh for self-occupied property)"
                    ),
                    'suggestions': ['100000', '150000', '200000'],
                    'type': 'text',
                    'data': None
                }
            else:
                user_data['has_home_loan'] = False
                # Move to expenses
                session_state['state'] = 'LIFESTYLE_EXPENSES'
                session_state['sub_state'] = 'ask_monthly_expenses'
                marital = user_data.get('marital_status', 'single')
                if marital == 'married':
                    prompt = (
                        "🏡 No home loan. Noted!\n\n"
                        "💸 What are your approximate **total household monthly expenses**?\n"
                        "(Include food, utilities, transport, children expenses, etc.)"
                    )
                else:
                    prompt = (
                        "🏡 No home loan. Noted!\n\n"
                        "💸 What are your approximate **monthly living expenses**?\n"
                        "(Include food, utilities, transport, etc.)"
                    )
                return {
                    'response': prompt,
                    'suggestions': ['20000', '30000', '40000', '50000'],
                    'type': 'text',
                    'data': None
                }

        # Sub-state: home loan interest
        if sub_state == 'ask_home_loan_interest':
            interest = self._parse_number(msg)
            if interest is None:
                interest = 0
            user_data['home_loan_interest'] = min(interest, 200000)
            session_state['state'] = 'LIFESTYLE_EXPENSES'
            session_state['sub_state'] = 'ask_monthly_expenses'
            marital = user_data.get('marital_status', 'single')
            if marital == 'married':
                prompt = (
                    f"🏡 Home Loan Interest: **₹{user_data['home_loan_interest']:,.0f}**/year\n\n"
                    "💸 What are your approximate **total household monthly expenses**?\n"
                    "(Include food, utilities, transport, children expenses, etc.)"
                )
            else:
                prompt = (
                    f"🏡 Home Loan Interest: **₹{user_data['home_loan_interest']:,.0f}**/year\n\n"
                    "💸 What are your approximate **monthly living expenses**?\n"
                    "(Include food, utilities, transport, etc.)"
                )
            return {
                'response': prompt,
                'suggestions': ['20000', '30000', '40000', '50000'],
                'type': 'text',
                'data': None
            }

        # Fallback
        return {
            'response': "I didn't catch that. Please answer the housing question.",
            'suggestions': ['Own', 'Rent'],
            'type': 'options',
            'data': None
        }

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def _handle_expenses(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_monthly_expenses')

        if sub_state == 'ask_monthly_expenses':
            expenses = self._parse_number(msg)
            if expenses is None or expenses < 0:
                return {
                    'response': "Please enter a valid monthly expense amount.",
                    'suggestions': ['20000', '30000', '40000', '50000'],
                    'type': 'text',
                    'data': None
                }
            user_data['monthly_expenses'] = expenses
            user_data['annual_expenses'] = expenses * 12

            session_state['state'] = 'LIFESTYLE_SAVINGS'
            session_state['sub_state'] = 'ask_monthly_savings'
            return {
                'response': (
                    f"💸 Monthly Expenses: **₹{expenses:,.0f}**\n\n"
                    "💰 Now let's talk about your **savings and investments**.\n\n"
                    "How much do you **save/invest per month** (total)?"
                ),
                'suggestions': ['5000', '10000', '20000', '30000', '50000'],
                'type': 'text',
                'data': None
            }

        return {
            'response': "Please enter your monthly expenses.",
            'suggestions': ['20000', '30000', '40000'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Savings & 80C
    # ------------------------------------------------------------------

    def _handle_savings(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_monthly_savings')

        if sub_state == 'ask_monthly_savings':
            savings = self._parse_number(msg)
            if savings is None or savings < 0:
                return {
                    'response': "Please enter a valid monthly savings amount.",
                    'suggestions': ['5000', '10000', '20000', '30000'],
                    'type': 'text',
                    'data': None
                }
            user_data['monthly_savings'] = savings
            user_data['annual_savings'] = savings * 12

            # Automatically compute Section 80C from monthly savings (up to 1.5L limit)
            user_data['sec_80c'] = min(user_data['annual_savings'], 150000)
            user_data['has_investments'] = user_data['sec_80c'] > 0

            # If married with children, ask tuition fees
            if user_data.get('marital_status') == 'married' and user_data.get('children_count', 0) > 0:
                session_state['sub_state'] = 'ask_tuition'
                return {
                    'response': (
                        f"💰 Monthly Savings: **₹{savings:,.0f}**\n\n"
                        "🎓 Do you pay **tuition fees** for your children?\n"
                        "If yes, enter the annual amount. (This is also under 80C.)\n"
                        "If no, type **0**."
                    ),
                    'suggestions': ['0', '25000', '50000', '100000'],
                    'type': 'text',
                    'data': None
                }

            # Move to CALCULATE directly
            session_state['state'] = 'CALCULATE'
            session_state['sub_state'] = None
            return self._handle_calculate(session_state)

        if sub_state == 'ask_tuition':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['tuition_fees'] = amt
            # Add tuition to 80C (it's part of the same limit)
            user_data['sec_80c'] = min(user_data.get('sec_80c', 0) + amt, 150000)

            # Move to CALCULATE directly
            session_state['state'] = 'CALCULATE'
            session_state['sub_state'] = None
            return self._handle_calculate(session_state)

        return {
            'response': "Please answer the savings question.",
            'suggestions': ['0', '10000', '20000'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Insurance (80D)
    # ------------------------------------------------------------------

    def _handle_insurance(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_health_self')

        if sub_state == 'ask_health_self':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['health_insurance_self'] = amt

            session_state['sub_state'] = 'ask_health_parents'
            return {
                'response': (
                    f"🏥 Health Insurance (Self/Family): **₹{amt:,.0f}**/year\n\n"
                    "How much is the annual **health insurance premium for your parents**?\n"
                    "(If none, type **0**)"
                ),
                'suggestions': ['0', '10000', '25000', '50000'],
                'type': 'text',
                'data': None
            }

        if sub_state == 'ask_health_parents':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['health_insurance_parents'] = amt

            session_state['sub_state'] = 'ask_parents_senior'
            return {
                'response': (
                    f"🏥 Health Insurance (Parents): **₹{amt:,.0f}**/year\n\n"
                    "Are your parents **senior citizens** (60+)?\n"
                    "(Senior citizen parents get a higher 80D limit of ₹50,000 vs ₹25,000)"
                ),
                'suggestions': ['Yes', 'No'],
                'type': 'options',
                'data': None
            }

        if sub_state == 'ask_parents_senior':
            user_data['parents_senior'] = msg_lower in ('yes', 'y', 'yeah', 'yep')

            session_state['state'] = 'LIFESTYLE_EDUCATION'
            session_state['sub_state'] = 'ask_education_loan'
            return {
                'response': (
                    f"👴 Parents senior citizen: **{'Yes' if user_data['parents_senior'] else 'No'}**\n\n"
                    "🎓 Do you have an **education loan**?\n"
                    "If yes, enter the annual **interest amount** (Section 80E — no upper limit!).\n"
                    "If no, type **0**."
                ),
                'suggestions': ['0', '25000', '50000', '100000'],
                'type': 'text',
                'data': None
            }

        return {
            'response': "Please answer the insurance question.",
            'suggestions': ['0', '10000', '25000'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Education Loan
    # ------------------------------------------------------------------

    def _handle_education(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_education_loan')

        if sub_state == 'ask_education_loan':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['education_loan_interest'] = amt

            session_state['state'] = 'LIFESTYLE_OTHER'
            session_state['sub_state'] = 'ask_nps'
            return {
                'response': (
                    f"🎓 Education Loan Interest: **₹{amt:,.0f}**/year\n\n"
                    "🏦 Do you contribute to **NPS (National Pension System)**?\n"
                    "If yes, enter annual contribution (Section 80CCD(1B) — additional ₹50,000 deduction).\n"
                    "If no, type **0**."
                ),
                'suggestions': ['0', '25000', '50000'],
                'type': 'text',
                'data': None
            }

        return {
            'response': "Please enter your education loan interest amount (or 0).",
            'suggestions': ['0', '25000', '50000'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Other Deductions (NPS, Donations)
    # ------------------------------------------------------------------

    def _handle_other(self, msg, msg_lower, session_state):
        user_data = session_state['user_data']
        sub_state = session_state.get('sub_state', 'ask_nps')

        if sub_state == 'ask_nps':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['nps'] = min(amt, 50000)

            session_state['sub_state'] = 'ask_donations'
            return {
                'response': (
                    f"🏦 NPS Contribution: **₹{user_data['nps']:,.0f}**/year\n\n"
                    "🤝 Did you make any **charitable donations** (Section 80G)?\n"
                    "Enter the eligible donation amount. If none, type **0**."
                ),
                'suggestions': ['0', '5000', '10000', '25000'],
                'type': 'text',
                'data': None
            }

        if sub_state == 'ask_donations':
            amt = self._parse_number(msg)
            if amt is None:
                amt = 0
            user_data['donations'] = amt

            # All data collected — transition to CALCULATE
            session_state['state'] = 'CALCULATE'
            session_state['sub_state'] = None
            return self._handle_calculate(session_state)

        return {
            'response': "Please answer the current question.",
            'suggestions': ['0'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Calculate
    # ------------------------------------------------------------------

    def _handle_calculate(self, session_state):
        """Build deductions_data and compute taxes for both regimes."""
        user_data = session_state['user_data']
        gross_income = user_data.get('gross_income', 0)

        # Build deductions data for old regime
        deductions_data = {
            'age_group': user_data.get('age_group', 'below_60'),
            'sec_80c': user_data.get('sec_80c', 0),
            'nps': user_data.get('nps', 0),
            'health_insurance_self': user_data.get('health_insurance_self', 0),
            'health_insurance_parents': user_data.get('health_insurance_parents', 0),
            'parents_senior': user_data.get('parents_senior', False),
            'education_loan_interest': user_data.get('education_loan_interest', 0),
            'donations': user_data.get('donations', 0),
            'hra_exemption': user_data.get('hra_exemption', 0),
        }

        comparison = self.tax_engine.compare_regimes(gross_income, deductions_data)
        recommended_tax = comparison['new_regime']['total_tax'] if comparison['recommended'] == 'New Regime' else comparison['old_regime']['total_tax']

        monthly = self.tax_engine.get_monthly_breakdown(gross_income, recommended_tax)
        checklist = self.tax_engine.get_document_checklist(user_data)

        # Store results
        user_data['comparison'] = comparison
        user_data['monthly_breakdown'] = monthly
        user_data['checklist'] = checklist
        user_data['recommended_tax'] = recommended_tax

        session_state['state'] = 'SUMMARY'
        session_state['sub_state'] = None

        # Build the summary response
        new_r = comparison['new_regime']
        old_r = comparison['old_regime']

        response = (
            "📊 **Your Tax Computation is Ready!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **Gross Income:** ₹{gross_income:,.0f}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔵 **New Regime (FY 2025-26):**\n"
            f"   Standard Deduction: ₹{new_r['standard_deduction']:,.0f}\n"
            f"   Taxable Income: ₹{new_r['taxable_income']:,.0f}\n"
            f"   Tax: ₹{new_r['tax_before_rebate']:,.0f}\n"
            f"   Rebate 87A: -₹{new_r['rebate_87a']:,.0f}\n"
            f"   Surcharge: ₹{new_r['surcharge']:,.0f}\n"
            f"   Cess (4%): ₹{new_r['cess']:,.0f}\n"
            f"   **Total Tax: ₹{new_r['total_tax']:,.0f}**\n"
            f"   Effective Rate: {new_r['effective_rate']}%\n\n"
            "🟠 **Old Regime:**\n"
            f"   Total Deductions: ₹{old_r['total_deductions']:,.0f}\n"
            f"   Taxable Income: ₹{old_r['taxable_income']:,.0f}\n"
            f"   Tax: ₹{old_r['tax_before_rebate']:,.0f}\n"
            f"   Rebate 87A: -₹{old_r['rebate_87a']:,.0f}\n"
            f"   Surcharge: ₹{old_r['surcharge']:,.0f}\n"
            f"   Cess (4%): ₹{old_r['cess']:,.0f}\n"
            f"   **Total Tax: ₹{old_r['total_tax']:,.0f}**\n"
            f"   Effective Rate: {old_r['effective_rate']}%\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Recommended: {comparison['recommended']}**\n"
            f"💡 {comparison['reason']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 **Monthly Breakdown ({comparison['recommended']}):**\n"
            f"   Monthly Gross: ₹{monthly['monthly_gross']:,.0f}\n"
            f"   Monthly Tax: ₹{monthly['monthly_tax']:,.0f}\n"
            f"   **Monthly Take-Home: ₹{monthly['monthly_net']:,.0f}**\n\n"
            "What would you like to do next?"
        )

        return {
            'response': response,
            'suggestions': ['View Checklist', 'Financial Summary', 'Ask a Question', 'Start Over'],
            'type': 'comparison',
            'data': {
                'comparison': comparison,
                'monthly_breakdown': monthly,
                'checklist': checklist
            }
        }

    # ------------------------------------------------------------------
    # Summary / Post-Calculation
    # ------------------------------------------------------------------

    def _handle_summary(self, msg_lower, session_state):
        user_data = session_state['user_data']

        if 'checklist' in msg_lower or 'document' in msg_lower:
            checklist = user_data.get('checklist', [])
            lines = ["📋 **Your Personalized Document Checklist:**\n"]
            for i, item in enumerate(checklist, 1):
                lines.append(f"  {i}. **{item['doc']}** — {item['reason']}")
            lines.append("\n💡 Keep all documents ready before filing your ITR!")

            session_state['state'] = 'COMPLETE'
            return {
                'response': '\n'.join(lines),
                'suggestions': ['Financial Summary', 'Ask a Question', 'Start Over'],
                'type': 'checklist',
                'data': {'checklist': checklist}
            }

        if 'financial' in msg_lower or 'summary' in msg_lower:
            fin = self.get_financial_summary(session_state)
            response = (
                "📊 **Your Financial Summary:**\n\n"
                f"💰 Annual Income: ₹{fin['annual_income']:,.0f} (₹{fin['monthly_income']:,.0f}/month)\n"
                f"💸 Annual Expenses: ₹{fin['annual_expenses']:,.0f} (₹{fin['monthly_expenses']:,.0f}/month)\n"
                f"🏠 Annual Rent: ₹{fin.get('annual_rent', 0):,.0f}\n"
                f"💰 Annual Savings: ₹{fin['annual_savings']:,.0f} (₹{fin['monthly_savings']:,.0f}/month)\n"
                f"🏛️ Tax ({fin['recommended_regime']}): ₹{fin['annual_tax']:,.0f} (₹{fin['monthly_tax']:,.0f}/month)\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 **Net Take-Home: ₹{fin['annual_net']:,.0f}/year (₹{fin['monthly_net']:,.0f}/month)**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            session_state['state'] = 'COMPLETE'
            return {
                'response': response,
                'suggestions': ['View Checklist', 'Ask a Question', 'Start Over'],
                'type': 'summary',
                'data': fin
            }

        # FAQ or question
        faq = self._check_faq(msg_lower)
        if faq:
            return faq

        session_state['state'] = 'COMPLETE'
        return {
            'response': (
                "Your tax computation is complete! Here's what you can do:\n\n"
                "• **View Checklist** — See documents needed for filing\n"
                "• **Financial Summary** — See your complete financial overview\n"
                "• **Start Over** — Begin a new tax calculation\n"
                "• Ask me any tax-related question!"
            ),
            'suggestions': ['View Checklist', 'Financial Summary', 'Start Over'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------

    def _handle_complete(self, msg_lower, session_state):
        user_data = session_state['user_data']

        if 'checklist' in msg_lower or 'document' in msg_lower:
            checklist = user_data.get('checklist', [])
            lines = ["📋 **Your Personalized Document Checklist:**\n"]
            for i, item in enumerate(checklist, 1):
                lines.append(f"  {i}. **{item['doc']}** — {item['reason']}")
            lines.append("\n💡 Keep all documents ready before filing your ITR!")
            return {
                'response': '\n'.join(lines),
                'suggestions': ['Financial Summary', 'Ask a Question', 'Start Over'],
                'type': 'checklist',
                'data': {'checklist': checklist}
            }

        if 'financial' in msg_lower or 'summary' in msg_lower:
            fin = self.get_financial_summary(session_state)
            response = (
                "📊 **Your Financial Summary:**\n\n"
                f"💰 Annual Income: ₹{fin['annual_income']:,.0f} (₹{fin['monthly_income']:,.0f}/month)\n"
                f"💸 Annual Expenses: ₹{fin['annual_expenses']:,.0f} (₹{fin['monthly_expenses']:,.0f}/month)\n"
                f"🏠 Annual Rent: ₹{fin.get('annual_rent', 0):,.0f}\n"
                f"💰 Annual Savings: ₹{fin['annual_savings']:,.0f} (₹{fin['monthly_savings']:,.0f}/month)\n"
                f"🏛️ Tax ({fin['recommended_regime']}): ₹{fin['annual_tax']:,.0f} (₹{fin['monthly_tax']:,.0f}/month)\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 **Net Take-Home: ₹{fin['annual_net']:,.0f}/year (₹{fin['monthly_net']:,.0f}/month)**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            return {
                'response': response,
                'suggestions': ['View Checklist', 'Ask a Question', 'Start Over'],
                'type': 'summary',
                'data': fin
            }

        # FAQ
        faq = self._check_faq(msg_lower)
        if faq:
            return faq

        return {
            'response': (
                "Your tax computation is complete! 🎉\n\n"
                "You can:\n"
                "• **View Checklist** — Documents needed for filing\n"
                "• **Financial Summary** — Complete financial overview\n"
                "• **Start Over** — Begin a new calculation\n"
                "• Ask me any tax-related question!"
            ),
            'suggestions': ['View Checklist', 'Financial Summary', 'Start Over'],
            'type': 'text',
            'data': None
        }

    # ------------------------------------------------------------------
    # Financial Summary
    # ------------------------------------------------------------------

    def get_financial_summary(self, session_state):
        """Return a comprehensive financial summary dict."""
        user_data = session_state.get('user_data', {})
        gross = user_data.get('gross_income', 0)
        comparison = user_data.get('comparison', {})
        recommended = comparison.get('recommended', 'New Regime')

        if recommended == 'New Regime':
            tax = comparison.get('new_regime', {}).get('total_tax', 0)
        else:
            tax = comparison.get('old_regime', {}).get('total_tax', 0)

        monthly_expenses = user_data.get('monthly_expenses', 0)
        annual_expenses = user_data.get('annual_expenses', 0)
        monthly_savings = user_data.get('monthly_savings', 0)
        annual_savings = user_data.get('annual_savings', 0)
        annual_rent = user_data.get('rent_paid', 0)

        return {
            'annual_income': gross,
            'monthly_income': round(gross / 12) if gross else 0,
            'annual_expenses': annual_expenses,
            'monthly_expenses': monthly_expenses,
            'annual_rent': annual_rent,
            'annual_savings': annual_savings,
            'monthly_savings': monthly_savings,
            'recommended_regime': recommended,
            'annual_tax': tax,
            'monthly_tax': round(tax / 12) if tax else 0,
            'annual_net': gross - tax,
            'monthly_net': round((gross - tax) / 12) if gross else 0
        }

    # ------------------------------------------------------------------
    # FAQ Detection
    # ------------------------------------------------------------------

    def _check_faq(self, msg_lower):
        """Check if the message matches any FAQ keywords and return an answer."""
        if any(kw in msg_lower for kw in ('itr form', 'which form', 'itr-1', 'itr1', 'sahaj')):
            return {
                'response': self.FAQ_ANSWERS['itr_form'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        if any(kw in msg_lower for kw in ('deadline', 'due date', 'last date', 'filing date')):
            return {
                'response': self.FAQ_ANSWERS['deadline'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        if any(kw in msg_lower for kw in ('penalty', 'penalties', 'late filing', 'fine')):
            return {
                'response': self.FAQ_ANSWERS['penalty'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        if any(kw in msg_lower for kw in ('refund', 'refund status', 'tax refund')):
            return {
                'response': self.FAQ_ANSWERS['refund'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        if any(kw in msg_lower for kw in ('form 16', 'form16', 'form-16')):
            return {
                'response': self.FAQ_ANSWERS['form16'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        if any(kw in msg_lower for kw in ('26as', 'ais', 'form 26', 'annual information')):
            return {
                'response': self.FAQ_ANSWERS['26as'],
                'suggestions': ['Continue'],
                'type': 'text',
                'data': None
            }
        return None

    # ------------------------------------------------------------------
    # Number Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_number(text):
        """Parse a number from text supporting Indian conventions.

        Supported formats:
            12 lakh / 12 lakhs / 12L  → 1200000
            1.5 lakh                  → 150000
            12,00,000 / 1200000       → 1200000
            50k                       → 50000
            50000                     → 50000
            1.2 cr / 1.2 crore        → 12000000
        Returns None if parsing fails.
        """
        if not text:
            return None

        text = text.strip().lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()

        # Handle "lakh" / "lakhs" / "lac"
        match = re.search(r'([\d.]+)\s*(lakh|lakhs|lac|l)\b', text)
        if match:
            return float(match.group(1)) * 100000

        # Handle "crore" / "cr"
        match = re.search(r'([\d.]+)\s*(crore|crores|cr)\b', text)
        if match:
            return float(match.group(1)) * 10000000

        # Handle "k"
        match = re.search(r'([\d.]+)\s*k\b', text)
        if match:
            return float(match.group(1)) * 1000

        # Handle percentage
        match = re.search(r'([\d.]+)\s*%', text)
        if match:
            return float(match.group(1))

        # Plain number
        match = re.search(r'[\d.]+', text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None

        return None
