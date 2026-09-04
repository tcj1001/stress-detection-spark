package com.stress.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@Data
public class RegisterRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(max = 50, message = "用户名最多50位")
    private String nickname;

    @NotBlank(message = "账号不能为空")
    @Size(min = 3, max = 50, message = "账号3-50位")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, message = "密码至少6位")
    private String password;
}
