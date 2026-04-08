import flet as ft
import requests
import json

# Backend API Configuration
API_BASE_URL = "http://localhost:8080/api"

class CDCVoucherApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "CDC Voucher System"
        self.page.window_width = 900
        self.page.window_height = 800
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        
        self.render_home()
    
    def render_home(self):
        """Main hub with all system options"""
        self.page.clean()
        
        title = ft.Text(
            "CDC Voucher System",
            size=40,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_900
        )
        
        subtitle = ft.Text(
            "Integrated Management Portal",
            size=16,
            color=ft.Colors.GREY_700
        )
        
        buttons = [
            self._create_nav_button(
                "🏠 Household Registration",
                "Register new households for CDC vouchers",
                ft.Colors.BLUE_100,
                self.show_household_registration
            ),
            self._create_nav_button(
                "👨‍👩‍👧 Household Portal",
                "Login to view and activate vouchers",
                ft.Colors.GREEN_100,
                self.show_household_portal
            ),
            self._create_nav_button(
                "🏪 Merchant Registration",
                "Register as a merchant partner",
                ft.Colors.ORANGE_100,
                self.show_merchant_registration
            ),
            self._create_nav_button(
                "💳 Merchant Portal",
                "Login to redeem customer vouchers",
                ft.Colors.PURPLE_100,
                self.show_merchant_portal
            ),
            self._create_nav_button(
                "📊 Analytics Dashboard",
                "View system statistics and insights",
                ft.Colors.PINK_100,
                self.show_analytics
            ),
        ]
        
        self.page.add(
            ft.Column(
                [
                    ft.Container(height=20),
                    title,
                    subtitle,
                    ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                    *buttons,
                    ft.Container(height=20)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
                scroll=ft.ScrollMode.AUTO
            )
        )
    
    def _create_nav_button(self, title, subtitle, color, on_click):
        """Helper to create navigation buttons"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, size=12, color=ft.Colors.GREY_700)
                ],
                spacing=5
            ),
            width=600,
            padding=20,
            bgcolor=color,
            border_radius=10,
            on_click=on_click,
            ink=True
        )
    
    def _create_header(self, title, subtitle=""):
        """Create page header with back button"""
        return ft.Column([
            ft.TextButton(
                "← Back to Home",
                on_click=lambda e: self.render_home()
            ),
            ft.Text(title, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Text(subtitle, size=14, color=ft.Colors.GREY_600) if subtitle else ft.Container(),
            ft.Divider()
        ])
    
    # ================== Household Registration ==================
    def show_household_registration(self, e):
        """Household registration view"""
        self.page.clean()
        
        fin_input = ft.TextField(
            label="FIN/NRIC",
            hint_text="e.g., S1234567A",
            width=400
        )
        
        result_text = ft.Text(size=14)
        result_container = ft.Container(
            content=result_text,
            visible=False,
            padding=15,
            border_radius=5
        )
        
        def register(e):
            if not fin_input.value:
                self._show_error(result_container, result_text, "Please enter FIN/NRIC")
                return
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/household/register",
                    json={"fin": fin_input.value}
                )
                
                data = response.json()
                
                if response.status_code in [200, 201] and data.get("success"):
                    if data.get("existing"):
                        self._show_info(
                            result_container, 
                            result_text,
                            f"Already registered!\nHousehold ID: {data['household_id']}"
                        )
                    else:
                        self._show_success(
                            result_container,
                            result_text,
                            f"Registration successful!\nYour Household ID: {data['household_id']}"
                        )
                        fin_input.value = ""
                else:
                    self._show_error(result_container, result_text, data.get("error", "Registration failed"))
            except Exception as ex:
                self._show_error(result_container, result_text, f"Connection error: {str(ex)}")
            
            self.page.update()
        
        self.page.add(
            ft.Column([
                self._create_header("Household Registration", "Register your household to receive CDC vouchers"),
                ft.Container(height=20),
                fin_input,
                ft.ElevatedButton(
                    "Register",
                    on_click=register,
                    bgcolor=ft.Colors.BLUE,
                    color="white",
                    width=200
                ),
                result_container,
                ft.Container(height=20)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO)
        )
    
    # ================== Household Portal ==================
    def show_household_portal(self, e):
        """Household login view"""
        self.page.clean()
        
        hid_input = ft.TextField(
            label="Household ID",
            hint_text="e.g., H0001",
            width=400
        )
        
        error_text = ft.Text(color=ft.Colors.RED)
        
        def login(e):
            if not hid_input.value:
                error_text.value = "Please enter Household ID"
                self.page.update()
                return
            
            try:
                response = requests.get(f"{API_BASE_URL}/household/{hid_input.value.strip()}/balance")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.show_voucher_selection(hid_input.value.strip(), data)
                    else:
                        error_text.value = "Household not found"
                else:
                    error_text.value = "Household not found"
            except Exception as ex:
                error_text.value = f"Connection error: {str(ex)}"
            
            self.page.update()
        
        self.page.add(
            ft.Column([
                self._create_header("Household Portal", "Login to view and use your vouchers"),
                ft.Container(height=30),
                hid_input,
                ft.ElevatedButton(
                    "Login",
                    on_click=login,
                    bgcolor=ft.Colors.GREEN,
                    color="white",
                    width=200
                ),
                error_text,
                ft.Container(height=20)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO)
        )
    
    def show_voucher_selection(self, household_id, balance_data):
        """Show voucher grid for selection"""
        self.page.clean()
        
        selected_vouchers = []
        voucher_state = balance_data["voucher_state"]
        total_balance = balance_data["total_balance"]
        
        # Header with balance
        balance_text = ft.Text(
            f"Available Balance: ${total_balance}",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700
        )
        
        selected_text = ft.Text(
            "Selected: $0",
            size=18,
            color=ft.Colors.BLUE_700
        )
        
        # Proceed button
        proceed_btn = ft.ElevatedButton(
            "Activate Selected Vouchers",
            visible=False,
            bgcolor=ft.Colors.GREEN,
            color="white",
            on_click=lambda e: self.activate_vouchers(household_id, selected_vouchers)
        )
        
        def update_selection_display():
            total = sum(int(v.split("-")[0][1:]) for v in selected_vouchers)
            selected_text.value = f"Selected: ${total} ({len(selected_vouchers)} vouchers)"
            proceed_btn.visible = len(selected_vouchers) > 0
            self.page.update()
        
        # Create voucher buttons
        voucher_buttons = []
        for denom, status_arr in voucher_state.items():
            for idx, status in enumerate(status_arr):
                code = f"V{int(denom):02d}-{idx+1:04d}-{household_id}"
                is_used = (status == 1)
                
                def make_handler(v_code, v_denom):
                    def handler(e):
                        btn = e.control
                        if v_code in selected_vouchers:
                            selected_vouchers.remove(v_code)
                            btn.bgcolor = ft.Colors.WHITE
                        else:
                            selected_vouchers.append(v_code)
                            btn.bgcolor = ft.Colors.LIGHT_BLUE_100
                        btn.update()
                        update_selection_display()
                    return handler
                
                btn = ft.ElevatedButton(
                    f"${denom}",
                    width=80,
                    height=60,
                    bgcolor=ft.Colors.GREY_300 if is_used else ft.Colors.WHITE,
                    color=ft.Colors.GREY_700 if is_used else ft.Colors.BLACK,
                    disabled=is_used,
                    on_click=make_handler(code, denom) if not is_used else None
                )
                
                voucher_buttons.append(btn)
        
        # Layout
        self.page.add(
            ft.Column([
                self._create_header(f"Household: {household_id}"),
                balance_text,
                ft.Divider(),
                ft.Row([
                    selected_text,
                    proceed_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Select vouchers to use:", weight=ft.FontWeight.BOLD),
                ft.Text("(Click vouchers to select/deselect)", size=12, color=ft.Colors.GREY),
                ft.Container(
                    content=ft.GridView(
                        controls=voucher_buttons,
                        max_extent=100,
                        child_aspect_ratio=1.2,
                        spacing=10,
                        run_spacing=10
                    ),
                    height=500
                ),
                ft.Container(height=20)
            ], scroll=ft.ScrollMode.AUTO)
        )
    
    def activate_vouchers(self, household_id, voucher_codes):
        """Activate selected vouchers and show barcode"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/voucher/activate",
                json={"voucher_codes": voucher_codes}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.show_activation_result(household_id, data)
                else:
                    self._show_dialog("Error", data.get("error", "Activation failed"))
            else:
                self._show_dialog("Error", "Activation failed")
        except Exception as ex:
            self._show_dialog("Error", f"Connection error: {str(ex)}")
    
    def show_activation_result(self, household_id, activation_data):
        """Display barcode for merchant scanning"""
        self.page.clean()
        
        barcode_img = ft.Image(
            src=f"data:image/png;base64,{activation_data['barcode_image']}",
            width=400,
            height=200
        )
        
        self.page.add(
            self._create_header("Vouchers Activated"),
            ft.Column([
                ft.Container(height=20),
                ft.Text(
                    "Show this barcode to the merchant",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(
                    content=barcode_img,
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=10
                ),
                ft.Text(
                    activation_data['barcode'],
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900
                ),
                ft.Divider(),
                ft.Text(
                    f"Total Amount: ${activation_data['total_amount']}",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREEN_700
                ),
                ft.Text(
                    f"Vouchers: {len(activation_data['voucher_codes'])}",
                    size=16,
                    color=ft.Colors.GREY_700
                ),
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Done",
                    on_click=lambda e: self.render_home(),
                    bgcolor=ft.Colors.BLUE,
                    color="white"
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    
    # ================== Merchant Registration ==================
    def show_merchant_registration(self, e):
        """Merchant registration view"""
        self.page.clean()
        
        name_input = ft.TextField(label="Merchant Name", width=400)
        bank_dropdown = ft.Dropdown(
            label="Bank",
            width=400,
            options=[
                ft.dropdown.Option("DBS Bank Ltd"),
                ft.dropdown.Option("OCBC Bank"),
                ft.dropdown.Option("UOB Bank"),
                ft.dropdown.Option("POSB Bank"),
                ft.dropdown.Option("Maybank Singapore"),
                ft.dropdown.Option("Standard Chartered Bank"),
                ft.dropdown.Option("HSBC Singapore"),
                ft.dropdown.Option("Citibank Singapore"),
            ]
        )
        account_input = ft.TextField(
            label="Account Number (9 digits)",
            width=400,
            max_length=9,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        holder_input = ft.TextField(label="Account Holder Name", width=400)
        
        result_text = ft.Text(size=14)
        result_container = ft.Container(
            content=result_text,
            visible=False,
            padding=15,
            border_radius=5
        )
        
        def register(e):
            # Validation
            if not all([name_input.value, bank_dropdown.value, account_input.value, holder_input.value]):
                self._show_error(result_container, result_text, "All fields are required")
                self.page.update()
                return
            
            # Check account number is exactly 9 digits
            if not account_input.value.isdigit() or len(account_input.value) != 9:
                self._show_error(result_container, result_text, "Account number must be exactly 9 digits")
                self.page.update()
                return
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/merchant/register",
                    json={
                        "name": name_input.value,
                        "bank": bank_dropdown.value,
                        "account_number": account_input.value,
                        "holder_name": holder_input.value
                    }
                )
                
                data = response.json()
                
                if data.get("success"):
                    if data.get("existing"):
                        # Already registered
                        self._show_info(
                            result_container,
                            result_text,
                            f"You are already registered!\nYour Merchant ID: {data['merchant_id']}"
                        )
                    else:
                        # New registration
                        self._show_success(
                            result_container,
                            result_text,
                            f"Registration successful!\nYour Merchant ID: {data['merchant_id']}\n\nPlease save this ID for login."
                        )
                        # Clear form
                        name_input.value = ""
                        bank_dropdown.value = None
                        account_input.value = ""
                        holder_input.value = ""
                else:
                    self._show_error(result_container, result_text, data.get("error", "Registration failed"))
            except Exception as ex:
                self._show_error(result_container, result_text, f"Connection error: {str(ex)}")
            
            self.page.update()
        
        self.page.add(
            ft.Column([
                self._create_header("Merchant Registration", "Register your business to accept CDC vouchers"),
                ft.Container(height=20),
                name_input,
                bank_dropdown,
                account_input,
                holder_input,
                ft.Container(height=10),
                ft.ElevatedButton(
                    "Register",
                    on_click=register,
                    bgcolor=ft.Colors.ORANGE,
                    color="white",
                    width=200
                ),
                result_container,
                ft.Container(height=20)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO)
        )
    
    # ================== Merchant Portal ==================
    def show_merchant_portal(self, e):
        """Merchant login view"""
        self.page.clean()
        
        mid_input = ft.TextField(
            label="Merchant ID",
            hint_text="e.g., M001",
            width=400
        )
        
        error_text = ft.Text(color=ft.Colors.RED)
        
        def login(e):
            if not mid_input.value:
                error_text.value = "Please enter Merchant ID"
                self.page.update()
                return
            
            try:
                response = requests.get(f"{API_BASE_URL}/merchant/{mid_input.value.strip()}")
                
                if response.status_code == 200 and response.json().get("success"):
                    self.show_merchant_dashboard(mid_input.value.strip())
                else:
                    error_text.value = "Merchant not found"
            except Exception as ex:
                error_text.value = f"Connection error: {str(ex)}"
            
            self.page.update()
        
        self.page.add(
            ft.Column([
                self._create_header("Merchant Portal", "Login to redeem customer vouchers"),
                ft.Container(height=30),
                mid_input,
                ft.ElevatedButton(
                    "Login",
                    on_click=login,
                    bgcolor=ft.Colors.PURPLE,
                    color="white",
                    width=200
                ),
                error_text,
                ft.Container(height=20)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO)
        )
    
    def show_merchant_dashboard(self, merchant_id):
        """Merchant dashboard for redemption"""
        self.page.clean()
        
        barcode_input = ft.TextField(
            label="Scan/Enter Barcode",
            hint_text="13-digit barcode",
            width=400,
            autofocus=True
        )
        
        result_text = ft.Text(size=14)
        result_container = ft.Container(
            content=result_text,
            visible=False,
            padding=15,
            border_radius=5
        )
        
        def redeem(e):
            if not barcode_input.value:
                self._show_error(result_container, result_text, "Please enter barcode")
                self.page.update()
                return
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/merchant/{merchant_id}/redeem",
                    json={"barcode": barcode_input.value}
                )
                
                data = response.json()
                
                if response.status_code == 200 and data.get("success"):
                    self._show_success(
                        result_container,
                        result_text,
                        f"✓ Redemption Successful!\n\nAmount: ${data['amount_redeemed']}\nTransaction ID: {data['transaction_id']}"
                    )
                    barcode_input.value = ""
                    barcode_input.focus()
                else:
                    self._show_error(result_container, result_text, data.get("error", "Redemption failed"))
            except Exception as ex:
                self._show_error(result_container, result_text, f"Connection error: {str(ex)}")
            
            self.page.update()
        
        def show_history(e):
            try:
                response = requests.get(f"{API_BASE_URL}/merchant/{merchant_id}/transactions")
                if response.status_code == 200:
                    data = response.json()
                    self.show_transaction_history(merchant_id, data.get("transactions", []))
            except Exception as ex:
                self._show_dialog("Error", f"Could not load history: {str(ex)}")
        
        self.page.add(
            self._create_header(f"Merchant Dashboard: {merchant_id}"),
            ft.Column([
                ft.Container(height=20),
                ft.Text("Scan customer barcode to redeem vouchers", size=16),
                ft.Container(height=20),
                barcode_input,
                ft.Row([
                    ft.ElevatedButton(
                        "Redeem",
                        on_click=redeem,
                        bgcolor=ft.Colors.BLUE,
                        color="white",
                        width=150
                    ),
                    ft.OutlinedButton(
                        "View History",
                        on_click=show_history,
                        width=150
                    )
                ], spacing=20),
                result_container,
                ft.Container(height=20)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO)
        )
    
    def show_transaction_history(self, merchant_id, transactions):
        """Show merchant transaction history"""
        self.page.clean()
        
        if not transactions:
            self.page.add(
                self._create_header(f"Transaction History: {merchant_id}"),
                ft.Text("No transactions yet", size=16, color=ft.Colors.GREY)
            )
            return
        
        # Create transaction cards
        tx_cards = []
        for tx in reversed(transactions[-10:]):  # Show last 10
            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(tx['transaction_id'], weight=ft.FontWeight.BOLD),
                        ft.Text(tx['total_amount'], size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"Household: {tx['household_id']}", size=12, color=ft.Colors.GREY),
                    ft.Text(f"Vouchers: {len(tx['vouchers'])}", size=12, color=ft.Colors.GREY),
                    ft.Text(f"Time: {tx['timestamp']}", size=12, color=ft.Colors.GREY),
                ]),
                padding=15,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10,
                width=600
            )
            tx_cards.append(card)
        
        self.page.add(
            self._create_header(f"Transaction History: {merchant_id}"),
            ft.Column(tx_cards, spacing=10, scroll=ft.ScrollMode.AUTO, height=600)
        )
    
    # ================== Analytics ==================
    def show_analytics(self, e):
        """Show system analytics"""
        self.page.clean()
        
        try:
            response = requests.get(f"{API_BASE_URL}/analytics/summary")
            if response.status_code == 200:
                data = response.json()
                summary = data['summary']
                
                # Create stat cards
                stat_cards = [
                    self._create_stat_card("Households", summary['total_households'], ft.Colors.BLUE_100),
                    self._create_stat_card("Merchants", summary['total_merchants'], ft.Colors.ORANGE_100),
                    self._create_stat_card("Transactions", summary['total_transactions'], ft.Colors.GREEN_100),
                ]
                
                voucher_stats = summary['vouchers']
                value_stats = summary['value']
                
                self.page.add(
                    ft.Column([
                        self._create_header("System Analytics", "Overview of CDC voucher system"),
                        ft.Row(stat_cards, alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                        ft.Divider(),
                        ft.Text("Voucher Statistics", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text("Total Issued:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{voucher_stats['total_issued']:,}")
                                ]),
                                ft.Row([
                                    ft.Text("Total Used:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{voucher_stats['total_used']:,}")
                                ]),
                                ft.Row([
                                    ft.Text("Available:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{voucher_stats['total_available']:,}")
                                ]),
                                ft.Row([
                                    ft.Text("Usage Rate:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{voucher_stats['usage_rate']}%")
                                ]),
                            ]),
                            padding=20,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=10,
                            width=600
                        ),
                        ft.Divider(),
                        ft.Text("Value Statistics", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text("Total Issued:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"${value_stats['total_issued']:,}")
                                ]),
                                ft.Row([
                                    ft.Text("Total Redeemed:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"${value_stats['total_redeemed']:,}")
                                ]),
                                ft.Row([
                                    ft.Text("Available:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"${value_stats['total_available']:,}")
                                ]),
                            ]),
                            padding=20,
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=10,
                            width=600
                        ),
                        ft.Container(height=20)
                    ], scroll=ft.ScrollMode.AUTO)
                )
        except Exception as ex:
            self.page.add(
                self._create_header("Analytics Error"),
                ft.Text(f"Could not load analytics: {str(ex)}", color=ft.Colors.RED)
            )
    
    def _create_stat_card(self, title, value, color):
        """Helper to create statistic cards"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, color=ft.Colors.GREY_700),
                ft.Text(str(value), size=36, weight=ft.FontWeight.BOLD)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=200,
            padding=20,
            bgcolor=color,
            border_radius=10
        )
    
    # ================== Helper Methods ==================
    def _show_success(self, container, text_control, message):
        """Show success message"""
        container.bgcolor = ft.Colors.GREEN_100
        text_control.value = message
        text_control.color = ft.Colors.GREEN_900
        container.visible = True
    
    def _show_error(self, container, text_control, message):
        """Show error message"""
        container.bgcolor = ft.Colors.RED_100
        text_control.value = message
        text_control.color = ft.Colors.RED_900
        container.visible = True
    
    def _show_info(self, container, text_control, message):
        """Show info message"""
        container.bgcolor = ft.Colors.BLUE_100
        text_control.value = message
        text_control.color = ft.Colors.BLUE_900
        container.visible = True
    
    def _show_dialog(self, title, message):
        """Show alert dialog"""
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dlg))]
        )
        self.page.open(dlg)

def main(page: ft.Page):
    app = CDCVoucherApp(page)

if __name__ == "__main__":
    ft.app(target=main)
