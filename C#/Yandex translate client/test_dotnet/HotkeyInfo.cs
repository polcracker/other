﻿using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;



namespace Translator
{
    public partial class HotkeyInfo : Form
    {
        public static HotkeyInfo Instance;
        public HotkeyInfo()
        {
            InitializeComponent();
        }

        private void HotkeyInfo_FormClosing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            this.Visible = false;
            e.Cancel = true;
        }
    }
}
